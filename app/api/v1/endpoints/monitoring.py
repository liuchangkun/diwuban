from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def db_health_check():
    # 占位：后续调用 public.database_health_check()
    return {"db": "healthy"}
