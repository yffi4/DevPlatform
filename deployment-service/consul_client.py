"""
Consul client for service discovery and registration
"""
import httpx
import os
from typing import Dict, List, Optional, Any


class ConsulClient:
    """Client for interacting with Consul API"""

    def __init__(self, consul_addr: str = None):
        self.consul_addr = consul_addr or os.getenv("CONSUL_ADDR") or "http://127.0.0.1:8500"
        if not self.consul_addr.startswith("http://") and not self.consul_addr.startswith("https://"):
            self.consul_addr = f"http://{self.consul_addr}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def register_service(
        self,
        name: str,
        address: str,
        port: int,
        tags: List[str] = None,
        meta: Dict[str, str] = None,
        check: Dict[str, Any] = None,
    ) -> None:
        """
        Register a service with Consul

        Args:
            name: Service name
            address: Service address
            port: Service port
            tags: Service tags
            meta: Service metadata
            check: Health check configuration
        """
        url = f"{self.consul_addr}/v1/agent/service/register"

        payload = {
            "Name": name,
            "Address": address,
            "Port": port,
        }

        if tags:
            payload["Tags"] = tags

        if meta:
            payload["Meta"] = meta

        if check:
            payload["Check"] = check

        response = await self.client.put(url, json=payload)
        response.raise_for_status()

    async def deregister_service(self, service_id: str) -> None:
        """Deregister a service from Consul"""
        url = f"{self.consul_addr}/v1/agent/service/deregister/{service_id}"

        response = await self.client.put(url)
        response.raise_for_status()

    async def get_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Get service instances by name"""
        url = f"{self.consul_addr}/v1/catalog/service/{service_name}"

        response = await self.client.get(url)
        response.raise_for_status()

        return response.json()

    async def get_services(self) -> Dict[str, List[str]]:
        """Get all registered services"""
        url = f"{self.consul_addr}/v1/catalog/services"

        response = await self.client.get(url)
        response.raise_for_status()

        return response.json()

    async def health_check(self, service_name: str) -> List[Dict[str, Any]]:
        """Get health status of a service"""
        url = f"{self.consul_addr}/v1/health/service/{service_name}"

        response = await self.client.get(url)
        response.raise_for_status()

        return response.json()

    async def get_service_address(self, service_name: str) -> Optional[str]:
        """
        Get the address of a healthy service instance

        Returns:
            Service URL (e.g., http://localhost:8007) or None if not found
        """
        services = await self.get_service(service_name)

        if not services:
            return None

        # Get first healthy service
        for service in services:
            address = service.get("ServiceAddress") or service.get("Address")
            port = service.get("ServicePort")

            if address and port:
                return f"http://{address}:{port}"

        return None

    async def put_key(self, key: str, value: str) -> None:
        """Put a key-value pair in Consul KV store"""
        url = f"{self.consul_addr}/v1/kv/{key}"

        response = await self.client.put(url, content=value)
        response.raise_for_status()

    async def get_key(self, key: str) -> Optional[str]:
        """Get a value from Consul KV store"""
        url = f"{self.consul_addr}/v1/kv/{key}?raw"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def delete_key(self, key: str) -> None:
        """Delete a key from Consul KV store"""
        url = f"{self.consul_addr}/v1/kv/{key}"

        response = await self.client.delete(url)
        response.raise_for_status()

    async def get_user_services(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all services deployed by a specific user

        This queries Consul catalog for services with user-{user_id} tag
        """
        all_services = await self.get_services()
        user_services = []

        for service_name, tags in all_services.items():
            if f"user-{user_id}" in tags:
                service_details = await self.get_service(service_name)
                if service_details:
                    user_services.append({
                        "name": service_name,
                        "tags": tags,
                        "instances": service_details,
                    })

        return user_services

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
consul_client = ConsulClient()
