import os
import asyncio
import httpx
import redis
import json
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from utils import send_response, check_plusfriend
from asyncgpt import asyncgpt
from transformers import GPT2Tokenizer
from quart import jsonify


load_dotenv()

initial_response = {
    "version": "2.0",
    "useCallback": True,
}

async def send_response(callback_url, response):

    # 예외 처리를 위한 try-except 블록 추가
    try:
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        async with httpx.AsyncClient() as client:
            res = await client.post(callback_url, json=response, headers=headers)

        # 응답 상태 코드 확인
        if res.status_code == 200:
            print("Response successfully sent")
        else:
            print(f"Failed to send response: {res.status_code}, {res.text}")
    except Exception as e:
        print("An error occurred:", e)



async def send_email(user_request):

    vets_name = user_request.get('action',{}).get('detailParams',{}).get('동물병원',{}).get('origin')
    vets_contact = user_request.get('action',{}).get('detailParams',{}).get('sys_number',{}).get('origin')

    contexts = []
    contexts = user_request.get('contexts')[0]
    info_texts = contexts.get('params', {}).get('values',{}).get('value').split('\n')
    guardian_name = info_texts[0].split(":")[1].strip()
    guardian_contact = info_texts[1].split(":")[1].strip()
    guardian_email =  info_texts[2].split(":")[1].strip()
    pets_type =  info_texts[3].split(":")[1].strip()
    pets_name =  info_texts[4].split(":")[1].strip()
    pets_age =  info_texts[5].split(":")[1].strip()
    pets_sex =  info_texts[6].split(":")[1].strip()
    pets_symtoms =  info_texts[7].split(":")[1].strip()

    contents = f"""
                ================================[반려 동물 진료 신청서]==============================

                    의뢰 기관 : {vets_name}
                    기관 연락처 : {vets_contact}

                    -------------------------------반려 동물 정보-------------------------------

                    이름: {pets_name}
                    종(species): {pets_type}
                    나이: {pets_age}
                    성별: {pets_sex}
                    증상 및 세부 내용: {pets_symtoms}
                    
                    ---------------------------------보호자 정보--------------------------------

                    이름: {guardian_name}
                    전화번호: {guardian_contact}
                    이메일: {guardian_email}


                ====================================================================================
                """

    # STMP 서버의 url과 port 번호
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 465

    # 1. SMTP 서버 연결
    smtp = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)

    EMAIL_ADDR = os.getenv('MAIL_ID')
    EMAIL_PASSWORD = os.getenv('MAIL_PWD')

    # 2. SMTP 서버에 로그인
    smtp.login(EMAIL_ADDR, EMAIL_PASSWORD)

    # 3. MIME 형태의 이메일 메세지 작성
    message = EmailMessage()
    message.set_content(contents)
    message["Subject"] = "진료 신청서"
    message["From"] = EMAIL_ADDR  #보내는 사람의 이메일 계정
    message["To"] = guardian_email

    # 4. 서버로 메일 보내기
    smtp.send_message(message)

    # 5. 메일을 보내면 서버와의 연결 끊기
    smtp.quit()

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "textCard": {
                        "text": "진료 신청서 메일 전송 완료!",
                    },
                },
            ],
        }
    }

    return response



# 비동기 함수로 api 검색을 수행하고 콜백으로 결과를 보내는 함수
async def call_mail_send_response(request_info, callback_url):

    # 별도의 스레드에서 OCR 처리 실행
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, asyncio.run, send_email(request_info))

    await send_response(callback_url, response)  # 콜백 URL에 결과를 비동기적으로 전송




async def get_reserve(user_request):

    print(user_request)

    contexts = []
    contexts = user_request.get('contexts')
    vets_name = contexts[0].get('params',{}).get('동물병원',{}).get('value')
    vets_contact = contexts[0].get('params',{}).get('sys_number',{}).get('value')

    info_texts = []
    info_texts = user_request.get('action',{}).get('params',{}).get('values').split('\n')
    guardian_name = info_texts[0].split(":")[1].strip()
    guardian_contact = info_texts[1].split(":")[1].strip()
    guardian_email =  info_texts[2].split(":")[1].strip()
    pets_type =  info_texts[3].split(":")[1].strip()
    pets_name =  info_texts[4].split(":")[1].strip()
    pets_age =  info_texts[5].split(":")[1].strip()
    pets_sex =  info_texts[6].split(":")[1].strip()
    pets_symtoms =  info_texts[7].split(":")[1].strip()

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                    "title": vets_name,
                    "description": vets_contact,
                    "thumbnail": {
                        "imageUrl": "https://talk.kakaocdn.net/dna/caxHwI/bl59REXackH/guUdfftQV52UhQECH1JBkV/i_a5a41137ed26.png?credential=zf3biCPbmWRjbqf40YGePFLewdou7TIK&expires=1786081605&signature=7nBMdqYa4CVSXTPxZ%2F03OiHhItU%3D"
                    },
                    }
                },
                {
                    "textCard": {   
                        "text": f'''▸이름 : {guardian_name}\n▸연락처 : {guardian_contact}\n▸이메일 : {guardian_email}\n▸반려동물 종 : {pets_type}\n▸반려동물 이름 : {pets_name}\n▸반려동물 나이 : {pets_age}\n▸반려동물 나이 : {pets_sex}\n▸반려동물 나이 : {pets_symtoms}''',
                        "buttons": [
                            {
                            "label": "진료 신청",
                            "action": "message",
                            "messageText" : f"진료 신청 {vets_name} {vets_contact}"
                            },
                            # {
                            # "label": "정보 수정",
                            # "action": "block",
                            # "blockId": bid,
                            # "messageText" : "정보 수정"
                            # }
                      ]
                    },
                },
            ],
        }
    }

    return jsonify(response)



async def get_mail(user_request):

    print("get_mail ------- ", user_request)

    callback_url = user_request.get('userRequest', {}).get('callbackUrl')

    # 비동기 함수를 직접 호출하지 않고, asyncio.create_task를 사용하여 백그라운드에서 실행
    asyncio.create_task(call_mail_send_response(user_request, callback_url))


    return jsonify(initial_response)

