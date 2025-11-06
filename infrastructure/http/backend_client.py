import httpx
import logging

logger = logging.getLogger(__name__)


class BackendClient:
    """
    Cliente HTTP para comunicar Edge API con Backend Spring Boot.
    Envia datos de forma asíncrona para no bloquear el Edge API.
    """

    def __init__(self, backend_url: str, timeout: float = 10.0):
        self.backend_url = backend_url.rstrip('/')
        self.timeout = timeout
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def update_cubicle_status(
            self,
            cubicle_id: int,
            status: str
    ) -> bool:
        """
        Actualiza el status del cubículo en el backend.
        Solo envia el status (AVAILABLE or OCCUPIED).
        """
        try:
            payload = {
                "status": status
            }

            url = f"{self.backend_url}/api/v1/cubicles/{cubicle_id}/status"

            logger.info(f"Updating cubicle status in backend: {url}")
            logger.debug(f"Payload: {payload}")

            if not self.client:
                self.client = httpx.AsyncClient(timeout=self.timeout)

            response = await self.client.patch(url, json=payload)

            if response.status_code in [200, 201]:
                logger.info(f"Successfully updated status for cubicle {cubicle_id} to {status}")
                return True
            else:
                logger.warning(
                    f"Backend returned status {response.status_code} for cubicle {cubicle_id}: {response.text}"
                )
                return False

        except httpx.TimeoutException:
            logger.error(f"Timeout updating status for cubicle {cubicle_id} to backend")
            return False
        except httpx.RequestError as e:
            logger.error(f"Request error updating status for cubicle {cubicle_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating status for cubicle {cubicle_id}: {str(e)}")
            return False

    async def register_device_in_backend(
            self,
            device_id: str,
            device_type: str,
            branch_id: str,
            zone: str,
            position: str
    ) -> bool:
        """
        Registra dispositivo en el backend.
        """
        try:
            payload = {
                "deviceId": device_id,
                "deviceType": device_type,
                "branchId": branch_id,
                "zone": zone,
                "position": position
            }

            url = f"{self.backend_url}/api/v1/devices"

            logger.info(f"Registering device in backend: {url}")

            if not self.client:
                self.client = httpx.AsyncClient(timeout=self.timeout)

            response = await self.client.post(url, json=payload)

            if response.status_code in [200, 201]:
                logger.info(f"Successfully registered device {device_id} in backend")
                return True
            else:
                logger.warning(
                    f"Backend returned status {response.status_code} for device registration: {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error registering device in backend: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """
        Verifica si el backend esta disponible.
        """
        try:
            url = f"{self.backend_url}/actuator/health"

            if not self.client:
                self.client = httpx.AsyncClient(timeout=5.0)

            response = await self.client.get(url)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Backend health check failed: {str(e)}")
            return False