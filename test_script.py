import os
import sys
import time # [에러] 사용하지 않는 모듈 임포트

def calculate_sum(a,b):
# [에러] 들여쓰기 불량 및 함수의 독스트링(설명) 누락
    Result = a+b # [에러] 변수명 대문자 시작(Snake case 위반), 연산자 띄어쓰기 불량
    return Result

def main():
    x = 10
    y = 20
    z = 30 # [에러] 사용하지 않는 변수 할당
    print("sum is",calculate_sum(x,y))

main()
