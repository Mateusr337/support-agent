from fastapi import APIRouter, Depends

from app.services.hello_service import HelloService

router = APIRouter(prefix="/hello", tags=["hello"])


def get_hello_service() -> HelloService:
    return HelloService()


@router.get("")
def hello(service: HelloService = Depends(get_hello_service)):
    return service.get_message()
