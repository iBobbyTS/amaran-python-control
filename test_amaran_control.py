import base64
import unittest

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import amaran_control


class AmaranTokenTests(unittest.TestCase):
    def test_generate_token_uses_iv_tag_ciphertext_layout(self):
        nonce = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c"
        token = amaran_control.generate_token(amaran_control.DEFAULT_OPENAPI_SECRET, now=1_717_171_717, nonce=nonce)

        raw = base64.b64decode(token)
        self.assertEqual(raw[:12], nonce)

        tag = raw[12:28]
        ciphertext = raw[28:]
        key = base64.b64decode(amaran_control.DEFAULT_OPENAPI_SECRET)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext + tag, None)
        self.assertEqual(plaintext, b"1717171717")

    def test_generate_token_rejects_non_12_byte_nonce(self):
        with self.assertRaises(ValueError):
            amaran_control.generate_token(nonce=b"short")


class AmaranValueMappingTests(unittest.TestCase):
    def test_intensity_percent_to_raw_uses_openapi_0_to_1000_scale(self):
        self.assertEqual(amaran_control.intensity_percent_to_raw(1), 10)
        self.assertEqual(amaran_control.intensity_percent_to_raw(100), 1000)
        with self.assertRaises(ValueError):
            amaran_control.intensity_percent_to_raw(100.1)

    def test_gm_offset_and_side_mapping(self):
        self.assertEqual(amaran_control.gm_offset_to_raw(-1.0), 0)
        self.assertEqual(amaran_control.gm_offset_to_raw(0), 100)
        self.assertEqual(amaran_control.gm_offset_to_raw(1.0), 200)
        self.assertEqual(amaran_control.gm_side_to_raw("m"), 0)
        self.assertEqual(amaran_control.gm_side_to_raw("neutral"), 100)
        self.assertEqual(amaran_control.gm_side_to_raw("g"), 200)

    def test_build_openapi_request_uses_v2_shape(self):
        original_generate_token = amaran_control.generate_token
        try:
            amaran_control.generate_token = lambda _secret: "test-token"
            settings = amaran_control.OpenAPISettings(
                url="ws://127.0.0.1:33782",
                node_id="node-1",
                client_id=9,
                secret="unused",
            )

            payload = amaran_control.build_openapi_request(
                "set_cct",
                args={"cct": 1800, "intensity": 10, "gm": 200},
                settings=settings,
                request_id=123,
            )
        finally:
            amaran_control.generate_token = original_generate_token

        self.assertEqual(
            payload,
            {
                "version": 2,
                "type": "request",
                "client_id": 9,
                "request_id": 123,
                "node_id": "node-1",
                "action": "set_cct",
                "token": "test-token",
                "args": {"cct": 1800, "intensity": 10, "gm": 200},
            },
        )


class AmaranColorModeTests(unittest.TestCase):
    def test_set_hsi_requires_intensity_and_resolves_percent(self):
        calls = []
        original_send_openapi_request = amaran_control.send_openapi_request

        def fake_send_openapi_request(action, *, args=None, settings=None, include_events=False):
            calls.append((action, args, settings, include_events))
            return {"code": 0, "message": "ok", "data": args}

        try:
            amaran_control.send_openapi_request = fake_send_openapi_request
            response = amaran_control.set_hsi(120, 100, intensity_percent=1, include_events=True)
        finally:
            amaran_control.send_openapi_request = original_send_openapi_request

        self.assertEqual(response["data"], {"hue": 120, "sat": 100, "intensity": 10})
        self.assertEqual(calls[0][0], "set_hsi")
        self.assertTrue(calls[0][3])

        with self.assertRaises(ValueError):
            amaran_control.set_hsi(120, 100)

    def test_set_hsl_alias_calls_hsi(self):
        calls = []
        original_send_openapi_request = amaran_control.send_openapi_request

        def fake_send_openapi_request(action, *, args=None, settings=None, include_events=False):
            calls.append((action, args))
            return {"code": 0, "message": "ok", "data": args}

        try:
            amaran_control.send_openapi_request = fake_send_openapi_request
            response = amaran_control.set_hsl(240, 100, intensity=10)
        finally:
            amaran_control.send_openapi_request = original_send_openapi_request

        self.assertEqual(calls[0][0], "set_hsi")
        self.assertEqual(response["data"], {"hue": 240, "sat": 100, "intensity": 10})

    def test_set_rgb_accepts_optional_intensity_percent(self):
        calls = []
        original_send_openapi_request = amaran_control.send_openapi_request

        def fake_send_openapi_request(action, *, args=None, settings=None, include_events=False):
            calls.append((action, args))
            return {"code": 0, "message": "ok", "data": args}

        try:
            amaran_control.send_openapi_request = fake_send_openapi_request
            response = amaran_control.set_rgb(255, 0, 0, intensity_percent=1)
        finally:
            amaran_control.send_openapi_request = original_send_openapi_request

        self.assertEqual(calls[0][0], "set_rgb")
        self.assertEqual(response["data"], {"r": 255, "g": 0, "b": 0, "intensity": 10})

    def test_color_mode_range_validation(self):
        with self.assertRaises(ValueError):
            amaran_control.set_hsi(361, 100, intensity=10)
        with self.assertRaises(ValueError):
            amaran_control.set_hsi(0, 101, intensity=10)
        with self.assertRaises(ValueError):
            amaran_control.set_rgb(256, 0, 0)


class AmaranSetCctTests(unittest.TestCase):
    def test_set_cct_resolves_percent_and_gm_offset_without_network(self):
        calls = []
        original_send_openapi_request = amaran_control.send_openapi_request

        def fake_send_openapi_request(action, *, args=None, settings=None, include_events=False):
            calls.append((action, args, settings, include_events))
            return {"code": 0, "message": "ok", "data": args}

        try:
            amaran_control.send_openapi_request = fake_send_openapi_request
            response = amaran_control.set_cct(1800, intensity_percent=1, gm_offset=1.0, include_events=True)
        finally:
            amaran_control.send_openapi_request = original_send_openapi_request

        self.assertEqual(response["data"], {"cct": 1800, "intensity": 10, "gm": 200})
        self.assertEqual(calls[0][0], "set_cct")
        self.assertTrue(calls[0][3])

    def test_set_cct_rejects_ambiguous_intensity(self):
        with self.assertRaises(ValueError):
            amaran_control.set_cct(1800, intensity=10, intensity_percent=1)


if __name__ == "__main__":
    unittest.main()
