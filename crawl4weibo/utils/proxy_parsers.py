#!/usr/bin/env python

"""
Proxy API response parsers
"""

from typing import List
from urllib.parse import quote


def parse_plain_text_proxies(response_text: str) -> List[str]:
    """
    Parse plain text proxy response

    Supports formats:
    - Single line: "218.95.37.11:25152"
    - Multiple lines: one proxy per line
    - With protocol: "http://1.2.3.4:8080"
    - With auth: "218.95.37.11:25152:username:password"

    Args:
        response_text: Plain text response from proxy API

    Returns:
        List of proxy URLs in standard format

    Raises:
        ValueError: If response is empty or invalid
    """
    lines = [line.strip() for line in response_text.split("\n") if line.strip()]
    if not lines:
        raise ValueError("Proxy API returned empty text response")

    proxies = []
    for proxy_str in lines:
        try:
            proxy_url = _parse_single_proxy_string(proxy_str)
            proxies.append(proxy_url)
        except ValueError:
            continue

    if not proxies:
        raise ValueError("No valid proxies found in text response")

    return proxies


def _parse_single_proxy_string(proxy_str: str) -> str:
    """
    Parse a single proxy string

    Supports formats:
    - host:port
    - host:port:username:password
    - username:password@host:port
    - host:port@username:password
    - http://host:port (or https/socks4/socks5)

    Args:
        proxy_str: Proxy string in various formats

    Returns:
        Standardized proxy URL

    Raises:
        ValueError: If format is invalid
    """
    if proxy_str.startswith(("http://", "https://", "socks4://", "socks5://")):
        parts = proxy_str.split("://", 1)
        if len(parts) == 2 and ":" in parts[1]:
            return proxy_str
        else:
            raise ValueError(f"Invalid proxy format: {proxy_str}")

    if ":" not in proxy_str:
        raise ValueError(f"Invalid proxy format (missing port): {proxy_str}")

    if "@" in proxy_str:
        at_parts = proxy_str.split("@")
        if len(at_parts) == 2:
            left_part, right_part = at_parts

            if ":" in left_part and ":" in right_part:
                left_colons = left_part.split(":")
                right_colons = right_part.split(":")

                if len(left_colons) == 2 and len(right_colons) == 2:
                    try:
                        _validate_port(left_colons[1])
                        host, port = left_colons
                        username, password = right_colons
                        encoded_user = quote(username, safe="")
                        encoded_pass = quote(password, safe="")
                        return f"http://{encoded_user}:{encoded_pass}@{host}:{port}"
                    except ValueError:
                        pass

                    try:
                        _validate_port(right_colons[1])
                        username, password = left_colons
                        host, port = right_colons
                        encoded_user = quote(username, safe="")
                        encoded_pass = quote(password, safe="")
                        return f"http://{encoded_user}:{encoded_pass}@{host}:{port}"
                    except ValueError:
                        pass

    parts = proxy_str.split(":")

    if len(parts) == 4:
        host, port, username, password = parts
        _validate_port(port)
        encoded_user = quote(username, safe="")
        encoded_pass = quote(password, safe="")
        return f"http://{encoded_user}:{encoded_pass}@{host}:{port}"

    elif len(parts) == 2:
        host, port = parts
        _validate_port(port)
        return f"http://{host}:{port}"

    else:
        raise ValueError(f"Invalid proxy format: {proxy_str}")


def _validate_port(port_str: str):
    """Validate port number"""
    try:
        port_num = int(port_str)
    except ValueError:
        raise ValueError(f"Invalid port number (not a number): {port_str}")

    if not (1 <= port_num <= 65535):
        raise ValueError(f"Invalid port number (out of range): {port_str}")


def _parse_proxy_string_list(proxy_list: List[str]) -> List[str]:
    """
    Parse a list of proxy strings

    Args:
        proxy_list: List of proxy strings in various formats

    Returns:
        List of standardized proxy URLs

    Raises:
        ValueError: If list is empty or no valid proxies found
    """
    if not proxy_list:
        raise ValueError("Proxy list is empty")

    proxies = []
    for proxy_str in proxy_list:
        if isinstance(proxy_str, str):
            try:
                proxy_url = _parse_single_proxy_string(proxy_str)
                proxies.append(proxy_url)
            except ValueError:
                continue

    if not proxies:
        raise ValueError("No valid proxies found in proxy list")

    return proxies


def parse_json_proxies(response_data: dict) -> List[str]:
    """
    Parse JSON proxy response

    Supports formats:
    - {"proxy": "http://1.2.3.4:8080"}
    - {"ip": "1.2.3.4", "port": "8080"}
    - {"ip": "...", "port": "...", "username": "...", "password": "..."}
    - {"data": {"ip": "1.2.3.4", "port": 8080}}
    - {"data": [{"ip": "1.2.3.4", "port": 8080}, ...]}
    - {"data": ["218.95.37.11:25152:username:password", ...]}
    - {"data": {"proxy_list": ["218.95.37.11:25152:username:password", ...]}}
    - {"data": {"proxy_list": ["username:password@218.95.37.11:25152", ...]}}
    - {"data": {"proxy_list": ["218.95.37.11:25152@username:password", ...]}}

    Args:
        response_data: JSON response from proxy API

    Returns:
        List of proxy URLs in standard format

    Raises:
        ValueError: If response format is invalid
    """
    if "proxy" in response_data:
        proxy_str = response_data["proxy"]
        if isinstance(proxy_str, str):
            return [proxy_str]
        raise ValueError(f"Invalid proxy value type: {type(proxy_str)}")

    data = response_data.get("data", response_data)

    if isinstance(data, dict) and "proxy_list" in data:
        proxy_list = data["proxy_list"]
        if isinstance(proxy_list, list):
            return _parse_proxy_string_list(proxy_list)
        raise ValueError(f"Invalid proxy_list type: {type(proxy_list)}")

    if isinstance(data, list):
        if not data:
            raise ValueError("Proxy API returned empty data array")

        proxies = []
        for item in data:
            if isinstance(item, str):
                proxy_url = _parse_single_proxy_string(item)
                proxies.append(proxy_url)
            elif isinstance(item, dict):
                proxy_url = _parse_proxy_dict(item)
                proxies.append(proxy_url)
            else:
                continue

        if not proxies:
            raise ValueError("No valid proxies found in array")

        return proxies

    if isinstance(data, dict):
        proxy_url = _parse_proxy_dict(data)
        return [proxy_url]

    raise ValueError(f"Unable to parse proxy API response: {response_data}")


def _parse_proxy_dict(data: dict) -> str:
    """
    Parse proxy dictionary

    Args:
        data: Dictionary containing proxy info

    Returns:
        Standardized proxy URL

    Raises:
        ValueError: If required fields are missing
    """
    if "ip" not in data or "port" not in data:
        raise ValueError(f"Missing required fields (ip/port) in proxy dict: {data}")

    ip = str(data["ip"])
    port = str(data["port"])

    _validate_port(port)

    if "username" in data and "password" in data:
        username = str(data["username"])
        password = str(data["password"])
        encoded_user = quote(username, safe="")
        encoded_pass = quote(password, safe="")
        return f"http://{encoded_user}:{encoded_pass}@{ip}:{port}"

    return f"http://{ip}:{port}"


def default_proxy_parser(response_data) -> List[str]:
    """
    Default proxy API response parser

    Automatically detects response format and returns list of proxies.
    Supports both plain text and JSON formats.

    Args:
        response_data: Response from proxy API (str or dict)

    Returns:
        List of proxy URLs in standard format

    Raises:
        ValueError: If response format is invalid or no proxies found
    """
    if isinstance(response_data, str):
        return parse_plain_text_proxies(response_data)

    if isinstance(response_data, dict):
        return parse_json_proxies(response_data)

    raise ValueError(f"Unsupported response type: {type(response_data)}")
