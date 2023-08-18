import sys
import tracemalloc
from quart import Quart, request
from gpt_question import get_question
from kakaomap import get_map, get_review
from reservation import get_reserve, get_mail


tracemalloc.start()

application = Quart(__name__)


# 질문/폴백
@application.route("/question", methods=["POST"])
async def call_gpt():

    user_request = await request.json
    print(user_request)

    return await get_question(user_request)


# 병원검색 
@application.route("/map", methods=["POST"])
async def call_map():

    user_request = await request.json
    print(user_request)

    return await get_map(user_request)


# 후기검색 
@application.route("/review", methods=["POST"])
async def call_review():

    user_request = await request.json
    print(user_request)

    return await get_review(user_request)


# 진료예약1 - 보호자 정보 입력
@application.route("/reservation", methods=["POST"])
async def call_reserv():

    user_request = await request.json
    print(user_request)

    return await get_reserve(user_request)


# 메일
@application.route("/send_email", methods=["POST"])
async def call_mail():

    user_request = await request.json
    print(user_request)

    return await get_mail(user_request)



if __name__ == "__main__":
    tracemalloc.start()
    application.run(host='0.0.0.0', port=int(sys.argv[1]))