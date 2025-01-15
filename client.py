import math
import os
import requests

SERVER_URL = "http://localhost:8000" # FastAPI 서버 주소
FILE_PATH = "test.zip" # 업로드할 파일 경로
FILE_ID = "test" # 서버에서 구분할 file_id
CHUNK_SIZE = 1024 * 1024 * 10 # 10MB 단위로 끊어 전송
TIMEOUT = 5 # 네트워크 타임아웃


def get_server_offset(file_id):
    """ 서버에 현재까지 몇 바이트를 받았는지 물어보기 """
    url = f"{SERVER_URL}/resume-status/{file_id}"
    resp = requests.get(url, timeout=TIMEOUT)
    data = resp.json()
    if data.get("status") == "no-record":
        return 0
    return data.get("current_offset", 0)


def resume_upload(file_path):
    # 파일 크기
    total_size = os.path.getsize(file_path)
    # 서버가 이미 받은 offset(중간 재개 시점)을 가져옴 (없으면 0)
    current_offset = get_server_offset(FILE_ID)

    with open(file_path, "rb") as f:
        # 이미 받은 offset만큼 건너뛰기
        f.seek(current_offset)

        # 남은 바이트 계산
        remaining = total_size - current_offset
        total_chunks = math.ceil(remaining / CHUNK_SIZE)

        print(f"[시작] current_offset={int(current_offset / 20971520)}, total_size={total_size}, 남은 청크={total_chunks}")

        for _ in range(total_chunks):
            # 실제로 이번에 보낼 chunk
            chunk_data = f.read(CHUNK_SIZE)
            chunk_len = len(chunk_data)

            # 서버에 POST
            files = {
                "chunk_data": ("chunk_part", chunk_data)
            }
            data = {
                "file_id": FILE_ID,
                "offset": str(current_offset),
                "total_size": str(total_size)
            }
            try:
                resp = requests.post(f"{SERVER_URL}/resume-upload/",
                                     data=data, files=files, timeout=TIMEOUT)
                resp_json = resp.json()
                print(resp_json)

                if resp_json.get("status") == "completed":
                    # 업로드 완료
                    print("업로드가 완료되었습니다.")
                    break

                # 정상 전송되었다면, current_offset 업데이트
                current_offset += chunk_len

            except requests.exceptions.RequestException as e:
                # 네트워크 에러나 타임아웃 발생 시 여기서 중단
                print(f"전송 중 에러 발생: {e}")
                print("업로드를 중단하고, 나중에 재개할 수 있습니다.")
                break

if __name__ == "__main__":
    import sys
    try:
        resume_upload(FILE_PATH)
    except KeyboardInterrupt:
        print('연결 종료')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)