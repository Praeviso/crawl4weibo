#!/usr/bin/env python

"""
Test cases for proxy parsers
"""

import pytest

from crawl4weibo.utils.proxy_parsers import (
    default_proxy_parser,
    parse_json_proxies,
    parse_plain_text_proxies,
)


@pytest.mark.unit
class TestPlainTextParser:
    """Unit tests for plain text proxy parser"""

    def test_parse_single_proxy(self):
        """Test parsing single proxy without auth"""
        text = "218.95.37.11:25152"
        result = parse_plain_text_proxies(text)
        assert len(result) == 1
        assert result[0] == "http://218.95.37.11:25152"

    def test_parse_multiple_proxies(self):
        """Test parsing multiple proxies without auth"""
        text = "218.95.37.11:25152\n219.150.218.21:25089\n218.95.37.161:25015"
        result = parse_plain_text_proxies(text)
        assert len(result) == 3
        assert result[0] == "http://218.95.37.11:25152"
        assert result[1] == "http://219.150.218.21:25089"
        assert result[2] == "http://218.95.37.161:25015"

    def test_parse_single_proxy_with_auth(self):
        """Test parsing single proxy with authentication"""
        text = "218.95.37.11:25152:username:password"
        result = parse_plain_text_proxies(text)
        assert len(result) == 1
        assert result[0] == "http://username:password@218.95.37.11:25152"

    def test_parse_multiple_proxies_with_auth(self):
        """Test parsing multiple proxies with authentication"""
        text = "218.95.37.11:25152:user1:pass1\n219.150.218.21:25089:user2:pass2"
        result = parse_plain_text_proxies(text)
        assert len(result) == 2
        assert result[0] == "http://user1:pass1@218.95.37.11:25152"
        assert result[1] == "http://user2:pass2@219.150.218.21:25089"

    def test_parse_proxy_with_protocol(self):
        """Test parsing proxy that already has protocol"""
        text = "http://1.2.3.4:8080"
        result = parse_plain_text_proxies(text)
        assert len(result) == 1
        assert result[0] == "http://1.2.3.4:8080"

    def test_parse_multiple_proxies_with_protocol(self):
        """Test parsing multiple proxies with protocol"""
        text = "http://1.2.3.4:8080\nhttp://5.6.7.8:9090"
        result = parse_plain_text_proxies(text)
        assert len(result) == 2
        assert result[0] == "http://1.2.3.4:8080"
        assert result[1] == "http://5.6.7.8:9090"

    def test_parse_mixed_format_proxies(self):
        """Test parsing mix of proxies with and without protocol"""
        text = "http://1.2.3.4:8080\n5.6.7.8:9090\n10.11.12.13:3128:user:pass"
        result = parse_plain_text_proxies(text)
        assert len(result) == 3
        assert result[0] == "http://1.2.3.4:8080"
        assert result[1] == "http://5.6.7.8:9090"
        assert result[2] == "http://user:pass@10.11.12.13:3128"

    def test_parse_empty_text_raises_error(self):
        """Test parsing empty text raises ValueError"""
        with pytest.raises(ValueError, match="empty text response"):
            parse_plain_text_proxies("")

    def test_parse_whitespace_only_raises_error(self):
        """Test parsing whitespace only raises ValueError"""
        with pytest.raises(ValueError, match="empty text response"):
            parse_plain_text_proxies("   \n  \n  ")

    def test_parse_special_chars_in_credentials(self):
        """Test URL encoding of special characters in credentials"""
        text = "1.2.3.4:8080:user@domain:pass/word"
        result = parse_plain_text_proxies(text)
        assert len(result) == 1
        assert result[0] == "http://user%40domain:pass%2Fword@1.2.3.4:8080"

    def test_parse_ignores_empty_lines(self):
        """Test parser ignores empty lines"""
        text = "1.2.3.4:8080\n\n5.6.7.8:9090\n\n\n10.11.12.13:3128"
        result = parse_plain_text_proxies(text)
        assert len(result) == 3

    def test_parse_invalid_format_skipped(self):
        """Test invalid proxy formats are skipped"""
        text = "1.2.3.4:8080\ninvalid_format\n5.6.7.8:9090"
        result = parse_plain_text_proxies(text)
        assert len(result) == 2
        assert result[0] == "http://1.2.3.4:8080"
        assert result[1] == "http://5.6.7.8:9090"

    def test_parse_kuaidaili_format1(self):
        """Test parsing KuaiDaili format 1: username:password@host:port"""
        text = "username:password@218.95.37.11:25152"
        result = parse_plain_text_proxies(text)
        assert len(result) == 1
        assert result[0] == "http://username:password@218.95.37.11:25152"

    def test_parse_kuaidaili_format2(self):
        """Test parsing KuaiDaili format 2: host:port@username:password"""
        text = "218.95.37.11:25152@username:password"
        result = parse_plain_text_proxies(text)
        assert len(result) == 1
        assert result[0] == "http://username:password@218.95.37.11:25152"

    def test_parse_kuaidaili_format1_multiple(self):
        """Test parsing multiple proxies in KuaiDaili format 1"""
        text = "username:password@218.95.37.11:25152\nuser2:pass2@219.150.218.21:25089"
        result = parse_plain_text_proxies(text)
        assert len(result) == 2
        assert result[0] == "http://username:password@218.95.37.11:25152"
        assert result[1] == "http://user2:pass2@219.150.218.21:25089"

    def test_parse_kuaidaili_format2_multiple(self):
        """Test parsing multiple proxies in KuaiDaili format 2"""
        text = "218.95.37.11:25152@username:password\n219.150.218.21:25089@user2:pass2"
        result = parse_plain_text_proxies(text)
        assert len(result) == 2
        assert result[0] == "http://username:password@218.95.37.11:25152"
        assert result[1] == "http://user2:pass2@219.150.218.21:25089"


@pytest.mark.unit
class TestJsonParser:
    """Unit tests for JSON proxy parser"""

    def test_parse_single_proxy_dict(self):
        """Test parsing single proxy in dict format"""
        data = {"ip": "1.2.3.4", "port": "8080"}
        result = parse_json_proxies(data)
        assert len(result) == 1
        assert result[0] == "http://1.2.3.4:8080"

    def test_parse_single_proxy_with_auth(self):
        """Test parsing single proxy with authentication"""
        data = {
            "ip": "1.2.3.4",
            "port": "8080",
            "username": "user",
            "password": "pass",
        }
        result = parse_json_proxies(data)
        assert len(result) == 1
        assert result[0] == "http://user:pass@1.2.3.4:8080"

    def test_parse_proxy_field(self):
        """Test parsing response with proxy field"""
        data = {"proxy": "http://5.6.7.8:9090"}
        result = parse_json_proxies(data)
        assert len(result) == 1
        assert result[0] == "http://5.6.7.8:9090"

    def test_parse_nested_data(self):
        """Test parsing nested data field"""
        data = {"data": {"ip": "10.20.30.40", "port": 7777}}
        result = parse_json_proxies(data)
        assert len(result) == 1
        assert result[0] == "http://10.20.30.40:7777"

    def test_parse_array_of_dicts(self):
        """Test parsing array of proxy dicts"""
        data = {
            "data": [
                {"ip": "1.2.3.4", "port": "8080"},
                {"ip": "5.6.7.8", "port": "9090"},
                {"ip": "10.11.12.13", "port": "3128"},
            ]
        }
        result = parse_json_proxies(data)
        assert len(result) == 3
        assert result[0] == "http://1.2.3.4:8080"
        assert result[1] == "http://5.6.7.8:9090"
        assert result[2] == "http://10.11.12.13:3128"

    def test_parse_array_of_dicts_with_auth(self):
        """Test parsing array of proxy dicts with authentication"""
        data = {
            "data": [
                {"ip": "1.2.3.4", "port": "8080", "username": "user1", "password": "pass1"},
                {"ip": "5.6.7.8", "port": "9090", "username": "user2", "password": "pass2"},
            ]
        }
        result = parse_json_proxies(data)
        assert len(result) == 2
        assert result[0] == "http://user1:pass1@1.2.3.4:8080"
        assert result[1] == "http://user2:pass2@5.6.7.8:9090"

    def test_parse_array_of_strings(self):
        """Test parsing array of proxy strings"""
        data = {
            "data": [
                "218.95.37.11:25152:username:password",
                "219.150.218.21:25089:username:password",
                "218.95.37.161:25015:username:password",
            ]
        }
        result = parse_json_proxies(data)
        assert len(result) == 3
        assert result[0] == "http://username:password@218.95.37.11:25152"
        assert result[1] == "http://username:password@219.150.218.21:25089"
        assert result[2] == "http://username:password@218.95.37.161:25015"

    def test_parse_array_of_strings_no_auth(self):
        """Test parsing array of proxy strings without auth"""
        data = {"data": ["10.20.30.40:8080", "50.60.70.80:9090"]}
        result = parse_json_proxies(data)
        assert len(result) == 2
        assert result[0] == "http://10.20.30.40:8080"
        assert result[1] == "http://50.60.70.80:9090"

    def test_parse_special_chars_in_credentials(self):
        """Test URL encoding of special characters"""
        data = {
            "ip": "1.2.3.4",
            "port": "8080",
            "username": "user@domain",
            "password": "pass:word/123",
        }
        result = parse_json_proxies(data)
        assert len(result) == 1
        assert result[0] == "http://user%40domain:pass%3Aword%2F123@1.2.3.4:8080"

    def test_parse_empty_array_raises_error(self):
        """Test parsing empty array raises ValueError"""
        with pytest.raises(ValueError, match="empty data array"):
            parse_json_proxies({"data": []})

    def test_parse_mixed_array(self):
        """Test parsing array with both dicts and strings"""
        data = {
            "data": [
                {"ip": "1.2.3.4", "port": "8080"},
                "5.6.7.8:9090",
                {"ip": "10.11.12.13", "port": "3128"},
            ]
        }
        result = parse_json_proxies(data)
        assert len(result) == 3
        assert result[0] == "http://1.2.3.4:8080"
        assert result[1] == "http://5.6.7.8:9090"
        assert result[2] == "http://10.11.12.13:3128"

    def test_parse_kuaidaili_proxy_list_format1(self):
        """Test parsing KuaiDaili proxy_list format: host:port:username:password"""
        data = {
            "code": 0,
            "msg": "",
            "data": {
                "count": 10,
                "proxy_list": [
                    "218.95.37.11:25152:username:password",
                    "219.150.218.21:25089:username:password",
                    "218.95.37.161:25015:username:password",
                ],
            },
        }
        result = parse_json_proxies(data)
        assert len(result) == 3
        assert result[0] == "http://username:password@218.95.37.11:25152"
        assert result[1] == "http://username:password@219.150.218.21:25089"
        assert result[2] == "http://username:password@218.95.37.161:25015"

    def test_parse_kuaidaili_proxy_list_format2(self):
        """Test parsing KuaiDaili proxy_list format: username:password@host:port"""
        data = {
            "code": 0,
            "msg": "",
            "data": {
                "count": 10,
                "proxy_list": [
                    "username:password@218.95.37.11:25152",
                    "username:password@219.150.218.21:25089",
                    "username:password@218.95.37.161:25015",
                ],
            },
        }
        result = parse_json_proxies(data)
        assert len(result) == 3
        assert result[0] == "http://username:password@218.95.37.11:25152"
        assert result[1] == "http://username:password@219.150.218.21:25089"
        assert result[2] == "http://username:password@218.95.37.161:25015"

    def test_parse_kuaidaili_proxy_list_format3(self):
        """Test parsing KuaiDaili proxy_list format: host:port@username:password"""
        data = {
            "code": 0,
            "msg": "",
            "data": {
                "count": 10,
                "proxy_list": [
                    "218.95.37.11:25152@username:password",
                    "219.150.218.21:25089@username:password",
                    "218.95.37.161:25015@username:password",
                ],
            },
        }
        result = parse_json_proxies(data)
        assert len(result) == 3
        assert result[0] == "http://username:password@218.95.37.11:25152"
        assert result[1] == "http://username:password@219.150.218.21:25089"
        assert result[2] == "http://username:password@218.95.37.161:25015"


@pytest.mark.unit
class TestDefaultParser:
    """Unit tests for default proxy parser"""

    def test_parse_plain_text_single(self):
        """Test default parser with plain text single proxy"""
        result = default_proxy_parser("10.20.30.40:8080")
        assert len(result) == 1
        assert result[0] == "http://10.20.30.40:8080"

    def test_parse_plain_text_multiple(self):
        """Test default parser with plain text multiple proxies"""
        text = "1.2.3.4:8080\n5.6.7.8:9090"
        result = default_proxy_parser(text)
        assert len(result) == 2
        assert result[0] == "http://1.2.3.4:8080"
        assert result[1] == "http://5.6.7.8:9090"

    def test_parse_json_single(self):
        """Test default parser with JSON single proxy"""
        data = {"ip": "1.2.3.4", "port": "8080"}
        result = default_proxy_parser(data)
        assert len(result) == 1
        assert result[0] == "http://1.2.3.4:8080"

    def test_parse_json_multiple(self):
        """Test default parser with JSON multiple proxies"""
        data = {
            "data": [
                {"ip": "1.2.3.4", "port": "8080"},
                {"ip": "5.6.7.8", "port": "9090"},
            ]
        }
        result = default_proxy_parser(data)
        assert len(result) == 2
        assert result[0] == "http://1.2.3.4:8080"
        assert result[1] == "http://5.6.7.8:9090"

    def test_parse_unsupported_type_raises_error(self):
        """Test unsupported type raises ValueError"""
        with pytest.raises(ValueError, match="Unsupported response type"):
            default_proxy_parser(12345)

    def test_parse_invalid_format_raises_error(self):
        """Test invalid format raises ValueError"""
        with pytest.raises(ValueError):
            default_proxy_parser({"unexpected": "format"})
