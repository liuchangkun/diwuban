from fastapi import APIRouter

router = APIRouter()


@router.get("/measurements")
def get_measurements():
    # 占位：调用 api.get_measurements(...) 函数
    return {"items": [], "total": 0}
