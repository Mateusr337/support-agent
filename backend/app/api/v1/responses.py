from fastapi import status

UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": (
            "Authentication failed: missing token, invalid or expired token, "
            "or user not found"
        ),
    },
}

VALIDATION_ERROR_RESPONSE = {
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": "Request validation failed",
    },
}

NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "description": "Resource not found",
    },
}

BAD_REQUEST_RESPONSE = {
    status.HTTP_400_BAD_REQUEST: {
        "description": "Invalid request",
    },
}

CONFLICT_RESPONSE = {
    status.HTTP_409_CONFLICT: {
        "description": "Resource conflict",
    },
}

SERVICE_UNAVAILABLE_RESPONSE = {
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Dependency unavailable",
    },
}


def merge_responses(*response_maps: dict) -> dict:
    merged: dict = {}
    for response_map in response_maps:
        merged.update(response_map)
    return merged
