import asyncio
import os
import requests
import collections
import time

from quart import jsonify
from  utils import send_response, check_plusfriend
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException



collections.Callable = collections.abc.Callable


initial_response = {
    "version": "2.0",
    "useCallback": True,
}

    
# kakaomap api 검색 결과 반환 함수
def search_map(utterance):

    utterance = utterance + " 동물병원"

    # api에 keyword 전달
    url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    params = {'query': utterance,'page': 1}
    headers = {"Authorization": os.getenv('KAKAO_MAP_API_KEY')}
    places = requests.get(url, params=params, headers=headers).json()['documents']
    total = requests.get(url, params=params, headers=headers).json()['meta']['total_count']

    if total > 45:
        print(total,'개 중 45개 데이터밖에 가져오지 못했습니다!')
    else :
        print('모든 데이터를 가져왔습니다!')

    item_list = []

    for p in places:
        item = { 
            "itemList": [
                {
                    "title": "병원명",
                    "webLinkUrl": p.get('place_url'),
                    "description": p.get('place_name')
                },
                {
                    "title": "주소",
                    "webLinkUrl": p.get('place_url'),
                    "description": p.get('road_address_name')
                },
                {
                    "title": "연락처",
                    "webLinkUrl": p.get('place_url'),
                    "description": p.get('phone')
                }
            ],
            # "itemListAlignment": "left",
            "buttons": [
                {
                  "messageText": f"진료예약 {p.get('place_name')} {p.get('phone')}",
                  "action": "message",
                  "label": "진료 예약"
                },
                {
                  "label": "방문 후기",
                  "action": "message",
                  "messageText": f"방문 후기 {p.get('place_url')}",
                }
            ]
        }
        
        item_list.append(item)
    

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"총 {total}개의 검색결과 중 10개"
                    }
                },
                {
                    "carousel": {
                    "type": "itemCard",
                    "items": item_list
                    }
                }
            ],
            "quickReplies": [
 
                    {
                        "messageText": "메뉴",
                        "action": "message",
                        "label": "돌아가기"
                    }
            ]
        }
    }


    return response






# 비동기 함수로 api 검색을 수행하고 콜백으로 결과를 보내는 함수
async def call_map_and_send_response(utterance, callback_url):

    # 별도의 스레드에서 OCR 처리 실행
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, search_map, utterance)

    await send_response(callback_url, response)  # 콜백 URL에 결과를 비동기적으로 전송




    # 비동기 함수로 api 검색을 수행하고 콜백으로 결과를 보내는 함수
async def call_crawling_and_send_response(url, callback_url):

    # 별도의 스레드에서 OCR 처리 실행
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, crawl_review, url)

    await send_response(callback_url, response)  # 콜백 URL에 결과를 비동기적으로 전송

    



# 병원 검색 콜백 처리 함수
async def get_map(user_request):

    check_plusfriend(user_request)
        
    print(user_request)
    user_id = user_request.get('userRequest', {}).get('user', {}).get('id')
    callback_url = user_request.get('userRequest', {}).get('callbackUrl')
    print("callback_url: ", callback_url)

    uttrance = user_request.get('action', {}).get('detailParams', {}).get('input_sites',{}).get('origin')
    print("uttrance: ", uttrance)

    # 비동기 함수를 직접 호출하지 않고, asyncio.create_task를 사용하여 백그라운드에서 실행
    asyncio.create_task(call_map_and_send_response(uttrance, callback_url))

    return jsonify(initial_response)





# 후기 검색 콜백 처리 함수
async def get_review(user_request):

    user_id = user_request.get('userRequest', {}).get('user', {}).get('id')
    print("user_request: ", user_request)

    callback_url = user_request.get('userRequest', {}).get('callbackUrl')
    user_utterance = user_request.get('action', {}).get('detailParams', {}).get('review_url', {}).get('origin')
    print("user_utterance: ", user_utterance)

    # 비동기 함수를 직접 호출하지 않고, asyncio.create_task를 사용하여 백그라운드에서 실행
    asyncio.create_task(call_crawling_and_send_response(user_utterance, callback_url))
    
    # 처음에는 사용자에게 즉시 응답을 보냅니다.
    return jsonify(initial_response)




# 후기 크롤링 함수 
def crawl_review(base_url):

    try:
        #driver option 설정
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent= Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36')
        options.add_experimental_option("detach", True)

        #헤더 설정(윈도우10 기준)
        headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"}
        
        #-------------------------driver 실행------------------------#
        service = Service(executable_path='chromedriver.exe')
        driver = webdriver.Chrome(service=service, options = options)
        driver.implicitly_wait(10)
            

        #------------------상세페이지 별점, 후기 목록---------------#
        driver.get(base_url)
        time.sleep(2)
        
        vets_name = driver.find_element(By.CSS_SELECTOR,'#mArticle > div.cont_essential > div:nth-child(1) > div.place_details > div > h2').text
        vets_addr = driver.find_element(By.CLASS_NAME,'txt_address').text
        vets_contact = driver.find_element(By.CLASS_NAME,'txt_contact').text
        total_eval = driver.find_element(By.CSS_SELECTOR,'#mArticle > div.cont_evaluation > strong.total_evaluation > span').text
        time.sleep(2)

        print("병원 정보 : ", vets_name, vets_addr, vets_contact)


        # 더보기 확장 
        while int(total_eval) >= 3:  
            
            more_button = driver.find_element(By.CSS_SELECTOR, '#mArticle > div.cont_evaluation > div.evaluation_review > a')
            
            if more_button.text == '후기 더보기':
                more_button.send_keys(Keys.ENTER)
                time.sleep(1)
                
            else:
                break 

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        rates = soup.find_all(class_='ico_star inner_star')[2:-1]
        reviews = soup.find_all(name="p", attrs={"class": "txt_comment"})
        
        print("별점/리뷰 개수: ", len(rates), "개 ", len(reviews), "개 ")
        total_rate = str(soup.find_all(class_ = 'ico_star inner_star')[1])[47:50].replace('%','')
        
        vets_li = []
        row_li = []
        count = 1

        for rate, review in zip(rates, reviews):  
            
            if count == 26:
                break

            # if review.find(name="span").text == '':
            #     continue
                
            row={
                "title" :  "평점 " + str(rate)[47:50].replace('%',''), 
                "description" : review.find(name="span").text,
                "link": {
                    "web": base_url
                }
                }
            
            
            print("리뷰: ", review.find(name="span").text)
            
            
            if count % 5 == 0:

                row_li.append(row)
                vets_li.append({
                                "header": 
                                {
                                "title": "방문후기"
                                },
                                "items" : row_li
                                })
                row_li = []

            else:
                
                row_li.append(row)

            count += 1
        

        # 방문 후기가 없거나 3개 미만인 경우에 대한 예외 처리
        if not vets_li:
            vets_li.append({

                "header": {
                    "title": "방문후기"
                },
                "items": [
                    {
                        "title": "후기 없음",
                        "description": "방문 후기가 없습니다.",
                    }
                ],
                "quickReplies": [
                {
                    "messageText": "메뉴",
                    "action": "message",
                    "label": "돌아가기"
                }
                ]
            })


        response = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"평균 별점 {total_rate}"
                        }
                    },
                    {
                        "carousel": {
                        "type": "listCard",
                        "items": vets_li
                        }
                    }
                    ],
                 "quickReplies": [
                    {
                        "messageText": f"진료예약 {vets_name} {vets_contact}",
                        "action": "message",
                        "label": "진료 예약"
                    },
                    {
                        "messageText": "메뉴",
                        "action": "message",
                        "label": "돌아가기"
                    }
            ]  
            }
            }
        
        print(response)

    except NoSuchElementException as e:

        print("Error: Element not found")

        response = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "방문 후기가 없습니다."
                        }
                    }
                ],
                "quickReplies": [
                    {
                        "messageText": "메뉴",
                        "action": "message",
                        "label": "돌아가기"
                    }
                ]
            }
        }


    return response

