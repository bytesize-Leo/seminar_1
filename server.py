import os
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI()

# 업로드 진행 상태를 저장해둘 딕셔너리
upload_progress = {} # { file_id: { "filename": str, "current_offset": int, "total_size": int } }

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/resume-upload/")
async def resume_upload(
    file_id: str = Form(...),
    total_size: int = Form(...),
    chunk_data: UploadFile = File(...)
):
    """
    시연 시나리오:ㄴ
    1) 클라이언트가 file_id, offset, total_size, chunk_data(바이너리)로 요청
    2) 서버는 현재까지 업로드된 offset과 비교하여 이어붙임
    3) 클라이언트가 연결이 끊긴 뒤, 다시 이어서 전송해도 중간부터 재개
    """

    # 이미 저장 중인 파일 정보를 딕셔너리에 저장해둔 적이 없다면 등록
    if file_id not in upload_progress:
        # 임시로 "file_id.bin" 같은 식으로 최종 파일명을 정해둠
        filename = f"{file_id}.zip"
        upload_progress[file_id] = {
            "filename": filename,
            "current_offset": 0,
            "total_size": total_size
        }

    current_offset = upload_progress[file_id]["current_offset"]
    filename = upload_progress[file_id]["filename"]
    final_path = os.path.join(UPLOAD_DIR, filename)

    # chunk_data 읽어서 파일에 이어쓰기
    try:
        chunk_bytes = await chunk_data.read()   
    except:
        print('연결 끊어짐')

    chunk_size = len(chunk_bytes)

    # 파일에 append 모드로 이어붙이기
    # offset 위치로 이동하여 쓸 수도 있지만, 여기서는 current_offset == 파일 길이라는 전제(append)로 진행
    with open(final_path, "ab") as f:
        f.seek(current_offset) # 혹시나 해서 정확히 offset 위치로 이동
        f.write(chunk_bytes)

    # 서버가 기록하는 current_offset 업데이트
    upload_progress[file_id]["current_offset"] += chunk_size
    updated_offset = upload_progress[file_id]["current_offset"]

    # 만약 모든 바이트를 다 받았다면, 업로드 완료 처리
    if updated_offset == total_size:
        # 필요하다면 여기서 파일 무결성 체크(해시 등) 후 상태 업데이트
        # 더이상 이 file_id에 대해 업로드 진행할 필요가 없으니, 딕셔너리에서 제거 가능
        upload_progress.pop(file_id, None)

        return {
            "status": "completed",
            "message": f"Upload finished. File saved to {final_path}"
        }

    # 아직 남은 데이터가 있다면 in-progress 상태
    import math
    return {
        "status": "in-progress",
        "message": f"Received {math.ceil(updated_offset / 20971520)} / {int(math.ceil(total_size / 20971520))}"
    }


@app.get("/resume-status/{file_id}")
def get_resume_status(file_id: str):
    """
    클라이언트가 현재까지 서버가 얼마나 받았는지 확인할 수 있도록 하는 엔드포인트.
    """
    if file_id not in upload_progress:
        return {
            "file_id": file_id,
            "status": "no-record",
            "message": "No in-progress upload found or upload completed."
        }
    return {
        "file_id": file_id,
        "current_offset": upload_progress[file_id]["current_offset"],
        "total_size": upload_progress[file_id]["total_size"]
    }