import httpx
from quart import jsonify


# plus 친구인지 확인하는 함수
def check_plusfriend(user_request):

    # 플러스친구인지 확인해서, 친구가 아니면 친구요청 response
    if user_request.get('userRequest', {}).get('user', {}).get('properties', {}).get('isFriend') is not True:
        fail_response = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "채널 추가 후 이용 부탁드립니다."
                        }
                    }
                ]
            }
        }

        return jsonify(fail_response)
    else:
        pass




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