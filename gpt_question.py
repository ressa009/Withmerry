import os
import asyncio
import httpx
import redis
import json
from dotenv import load_dotenv
from utils import send_response, check_plusfriend
from asyncgpt import asyncgpt
from transformers import GPT2Tokenizer
from quart import jsonify



load_dotenv()

tokenizer = GPT2Tokenizer.from_pretrained("gpt2")


redis_client = redis.StrictRedis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True 
)



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





async def get_answer(user_utterance, callback_url, session_id):

    # 이전 대화 내역 조회
    redis_key = f"session:{session_id}"
    previous_conversations = redis_client.lrange(redis_key, -3, -1)

    # 이전 대화가 없을 경우 기본 대화 문맥 생성하고, 있다면 최근 세개만 불러오기
    if not previous_conversations:
        messages = [{"role": "user", "content": "너는 친절한 반려동물 전문가야. 대화할 때 한국어로 계속 대답해줘."},
                    {"role": "assistant", "content": "네 알겠습니다. 저는 친절한 반려동물 전문가입니다."}]
    else:
        messages = [json.loads(conversation_json) for conversation_json in previous_conversations]

    # 사용자 발화가 비어있을 경우 기본 값으로 설정
    if not user_utterance:
        user_utterance = "안녕"
    
    messages.append({"role": "user", "content": user_utterance})
    tokens = tokenizer.encode(str(messages))  # 토큰 수 세기
    if len(tokens) >= 6500 or len(messages) > 20:  # 적정한 수준으로 토큰 유지 로직
        messages.pop(0)
        if len(tokens) >= 7500:
            messages.pop(0)

    bot = asyncgpt.GPT(apikey=os.getenv('GPT_API_KEY'))
    completion = await bot.chat_complete(messages)
    answer = str(completion)

    messages.append({"role": "assistant", "content": answer})
    tokens = tokenizer.encode(str(messages))
    # 토큰 재확인
    if len(tokens) >= 6500 or len(messages) > 20:
        messages.pop(0)

    # 사용자와 chatgpt의 대화를 JSON 형태로 저장
    conversation = {"role": "user", "content": user_utterance}
    conversation_json = json.dumps(conversation)
    redis_client.rpush(redis_key, conversation_json)

    conversation = {"role": "assistant", "content": answer}
    conversation_json = json.dumps(conversation)
    redis_client.rpush(redis_key, conversation_json)

    # 이전 대화가 3개를 초과하는 경우 가장 오래된 대화 삭제
    if len(previous_conversations) >= 3:
        redis_client.ltrim(redis_key, -6, -1)

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": answer
                    }
                }
            ],
            "quickReplies": [
                  {
                    "messageText": "질문하기",
                    "action": "message",
                    "label": "계속 질문하기"
                  },
                  {
                    "messageText": "메뉴",
                    "action": "message",
                    "label": "다른 서비스 이용"
                  }
                ]
        }
    }
    # 답변 보내는 함수 호출
    print(response)
    await send_response(callback_url, response)







async def get_question(user_request):

    # 플러스친구인지 확인해서, 친구가 아니면 친구요청 response
    check_plusfriend(user_request)

    user_id = user_request.get('userRequest', {}).get('user', {}).get('properties', {}).get('plusfriendUserKey', '')
    callback_url = user_request.get('userRequest', {}).get('callbackUrl')
    print("callback_url: ", callback_url)
    user_utterance = user_request.get('action', {}).get('params', {}).get('question_contents')# 파라미터로 넘어온 변수명 주의
    if user_utterance == '':
        user_utterance = user_request.get('userRequest', {}).get('utterance')
    print("user_utterance: ", user_utterance)

    initial_response = {
        "version": "2.0",
        "useCallback": True,
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "콜백"
                    }
                }
            ],
            }
    }

    # 비동기 함수를 직접 호출하지 않고, asyncio.create_task를 사용하여 백그라운드에서 실행
    asyncio.create_task(get_answer(user_utterance, callback_url, user_id))

    return jsonify(initial_response)
