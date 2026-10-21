from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from openAPI.Negotiation_fail.routes.negotiation_fail_route import (
    router as negotiation_fail_router,
)
from utils.core_utils import get_int_setting, get_setting


app = FastAPI(
    title=get_setting("app", "name", "Negotiation Fail API"),
    version=get_setting("app", "version", "1.0.0"),
    description=get_setting(
        "app",
        "description",
        "Negotiation failed phase processing API",
    ),
)

app.include_router(
    negotiation_fail_router,
    prefix=get_setting("app", "api_prefix", ""),
    tags=["Negotiation Fail"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": "Invalid request: Case_Id is mandatory and must be an integer",
        },
    )


@app.get("/")
def health_check():
    return {
        "message": "Negotiation Fail API is running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "negotiation_fail_api.main:app",
        host=get_setting("app", "host", "0.0.0.0"),
        port=get_int_setting("app", "port", 5000),
        reload=True,
    )
