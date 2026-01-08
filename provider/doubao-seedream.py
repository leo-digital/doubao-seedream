from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class DoubaoSeedreamProvider(ToolProvider):

    DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str:
        base_url = (base_url or "").strip()
        if not base_url:
            return DoubaoSeedreamProvider.DEFAULT_ARK_BASE_URL
        if not (base_url.startswith("https://") or base_url.startswith("http://")):
            raise ValueError("ARK_BASE_URL must start with http:// or https://")
        return base_url.rstrip("/")

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            import json
            import urllib.request

            api_key = (credentials.get("ARK_API_KEY") or credentials.get("ark_api_key") or "").strip()
            if not api_key:
                raise ValueError("ARK_API_KEY is required")

            base_url = self._normalize_base_url(
                credentials.get("ARK_BASE_URL") or credentials.get("ark_base_url")
            )

            url = f"{base_url}/models"
            request = urllib.request.Request(
                url,
                method="GET",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status < 200 or response.status >= 300:
                    raise ValueError(f"Ark /models request failed with status={response.status}")
                payload = json.loads(response.read() or "{}")
                if not isinstance(payload, dict) or "data" not in payload:
                    raise ValueError(
                        "Ark credentials validated but /models response is unexpected; "
                        "please confirm ARK_BASE_URL points to /api/v3"
                    )
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))

    #########################################################################################
    # If OAuth is supported, uncomment the following functions.
    # Warning: please make sure that the sdk version is 0.4.2 or higher.
    #########################################################################################
    # def _oauth_get_authorization_url(self, redirect_uri: str, system_credentials: Mapping[str, Any]) -> str:
    #     """
    #     Generate the authorization URL for doubao-seedream OAuth.
    #     """
    #     try:
    #         """
    #         IMPLEMENT YOUR AUTHORIZATION URL GENERATION HERE
    #         """
    #     except Exception as e:
    #         raise ToolProviderOAuthError(str(e))
    #     return ""
        
    # def _oauth_get_credentials(
    #     self, redirect_uri: str, system_credentials: Mapping[str, Any], request: Request
    # ) -> Mapping[str, Any]:
    #     """
    #     Exchange code for access_token.
    #     """
    #     try:
    #         """
    #         IMPLEMENT YOUR CREDENTIALS EXCHANGE HERE
    #         """
    #     except Exception as e:
    #         raise ToolProviderOAuthError(str(e))
    #     return dict()

    # def _oauth_refresh_credentials(
    #     self, redirect_uri: str, system_credentials: Mapping[str, Any], credentials: Mapping[str, Any]
    # ) -> OAuthCredentials:
    #     """
    #     Refresh the credentials
    #     """
    #     return OAuthCredentials(credentials=credentials, expires_at=-1)
