""" Unit tests for ibflex.parser module """

import datetime
import unittest
from io import BytesIO
from unittest.mock import Mock, call, patch

import requests

from ibflex import Types, client, parser

RESPONSE_SUCCESS = (
    '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM EDT">'
    '<Status>Success</Status>'
    '<ReferenceCode>1234567890</ReferenceCode>'
    '<Url>https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement</Url>'
    '</FlexStatementResponse>'
)


RESPONSE_FAIL = (
    '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM EDT">'
    '<Status>Fail</Status>'
    '<ErrorCode>1012</ErrorCode>'
    '<ErrorMessage>Token has expired.</ErrorMessage>'
    '</FlexStatementResponse>'
)


FLEX_QUERY_RESPONSE = (
    '<FlexQueryResponse queryName="Test" type="AZ">'
    '<FlexStatements count="1">'
    '<FlexStatement accountId="U666777" fromDate="20070101" toDate="20071231" period="Foo" whenGenerated="20100505 12:30:45" />'
    '</FlexStatements>'
    '</FlexQueryResponse>'
)


def mock_response(*args, **kwargs) -> object:
    class MockResponse:
        def __init__(self, content: str):
            self._content = content

        @property
        def content(self) -> bytes:
            return bytes(self._content, encoding="utf8")

    params = kwargs["params"]
    token = params["t"]
    query = params["q"]

    if token == "DEADBEEF" and query == "0987654321":
        return MockResponse(RESPONSE_SUCCESS)
    elif token == "DEADBEEF" and query == "1234567890":
        return MockResponse(FLEX_QUERY_RESPONSE)

    return MockResponse(RESPONSE_FAIL)


@patch("requests.get", side_effect=requests.exceptions.Timeout)
class SubmitRequestTestCase(unittest.TestCase):
    def test_submit_request_retry(self, mock_requests_get):
        with self.assertRaises(requests.exceptions.Timeout):
            client.submit_request(
                url=client.REQUEST_URL,
                token="DEADBEEF",
                query="0987654321",
            )

        self.assertEqual(
            mock_requests_get.call_args_list,
            [
                call(
                    client.REQUEST_URL,
                    params={"v": "3", "t": "DEADBEEF", "q": "0987654321"},
                    headers={"user-agent": "Java"},
                    timeout=5,
                ),
                call(
                    client.REQUEST_URL,
                    params={"v": "3", "t": "DEADBEEF", "q": "0987654321"},
                    headers={"user-agent": "Java"},
                    timeout=10,
                ),
                call(
                    client.REQUEST_URL,
                    params={"v": "3", "t": "DEADBEEF", "q": "0987654321"},
                    headers={"user-agent": "Java"},
                    timeout=15,
                ),
            ],
        )


class SubmitRequestErrorResponseTestCase(unittest.TestCase):
    """A 4xx/5xx response must be returned to the caller, not retried forever.

    `requests.Response.__bool__` is `self.ok`, so the original
    `while (not response)` loop never exited on an error response.
    """

    class NotOkResponse:
        """Minimal stand-in for requests.Response, incl. its __bool__."""

        ok = False
        status_code = 500
        content = b"<html>500</html>"

        def __bool__(self):
            return self.ok

    @patch("requests.get")
    def test_error_response_returned_once(self, mock_requests_get):
        response = self.NotOkResponse()
        mock_requests_get.return_value = response

        output = client.submit_request(
            url=client.REQUEST_URL,
            token="DEADBEEF",
            query="0987654321",
        )

        self.assertIs(output, response)
        mock_requests_get.assert_called_once_with(
            client.REQUEST_URL,
            params={"v": "3", "t": "DEADBEEF", "q": "0987654321"},
            headers={"user-agent": "Java"},
            timeout=5,
        )


@patch("requests.get", side_effect=mock_response)
class RequestStatementTestCase(unittest.TestCase):
    def test_request_statement(self, mock_requests_get):
        #  `url` arg defaults to client.REQUEST_URL
        output = client.request_statement(
            token="DEADBEEF",
            query_id="0987654321",
        )

        mock_requests_get.assert_called_once_with(
            client.REQUEST_URL,
            params={"v": "3", "t": "DEADBEEF", "q": "0987654321"},
            headers={"user-agent": "Java"},
            timeout=5,
        )

        self.assertIsInstance(output, client.StatementAccess)
        self.assertEqual(
            output.timestamp,
            datetime.datetime(2012, 8, 28, 10, 37, tzinfo=datetime.timezone(
                datetime.timedelta(hours=-4)))
        )
        self.assertEqual(output.ReferenceCode, "1234567890")
        self.assertEqual(output.Url, client.STMT_URL)


@patch("requests.get", side_effect=mock_response)
class DownloadTestCase(unittest.TestCase):
    def test_request_statement(self, mock_requests_get: Mock):
        output = client.download(
            token="DEADBEEF",
            query_id="0987654321",
        )
        self.assertIsInstance(output, bytes)

        self.assertEqual(
            mock_requests_get.call_args_list,
            [
                call(
                    client.REQUEST_URL,
                    params={"v": "3", "t": "DEADBEEF", "q": "0987654321"},
                    headers={"user-agent": "Java"},
                    timeout=5,
                ),
                call(
                    client.STMT_URL,
                    params={"v": "3", "t": "DEADBEEF", "q": "1234567890"},
                    headers={"user-agent": "Java"},
                    timeout=5,
                ),
            ],
        )

        response = parser.parse(BytesIO(output))
        self.assertIsInstance(response, Types.FlexQueryResponse)


def make_mock_response(content: str):
    """Build a Mock that quacks like a requests.Response with given body."""
    resp = Mock(spec=requests.Response)
    resp.content = content.encode()
    return resp


class ParseStmtResponseTestCase(unittest.TestCase):
    """Coverage for the timezone fallback and the BadResponseError path."""

    def test_success(self):
        resp = make_mock_response(RESPONSE_SUCCESS)
        out = client.parse_stmt_response(resp)
        self.assertIsInstance(out, client.StatementAccess)
        self.assertEqual(out.ReferenceCode, "1234567890")

    def test_fail_returns_statement_error(self):
        resp = make_mock_response(RESPONSE_FAIL)
        out = client.parse_stmt_response(resp)
        self.assertIsInstance(out, client.StatementError)
        self.assertEqual(out.ErrorCode, "1012")

    def test_warn_returns_statement_error(self):
        body = (
            '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM EDT">'
            '<Status>Warn</Status>'
            '<ErrorCode>1004</ErrorCode>'
            '<ErrorMessage>Statement is incomplete.</ErrorMessage>'
            '</FlexStatementResponse>'
        )
        out = client.parse_stmt_response(make_mock_response(body))
        self.assertIsInstance(out, client.StatementError)
        self.assertEqual(out.ErrorCode, "1004")

    def test_unknown_timezone_falls_back_to_naive(self):
        """Timezones outside the known map parse as naive datetimes."""
        body = (
            '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM XYZ">'
            '<Status>Success</Status>'
            '<ReferenceCode>0</ReferenceCode>'
            '<Url>http://example.com</Url>'
            '</FlexStatementResponse>'
        )
        out = client.parse_stmt_response(make_mock_response(body))
        self.assertIsInstance(out, client.StatementAccess)
        self.assertIsNone(out.timestamp.tzinfo)

    def test_known_non_eastern_timezone(self):
        """CST/CDT/MST/MDT/PST/PDT/UTC/GMT all parse with the right offset."""
        cases = {
            "CST": -6, "CDT": -5,
            "MST": -7, "MDT": -6,
            "PST": -8, "PDT": -7,
            "UTC": 0, "GMT": 0,
        }
        for tz, hours in cases.items():
            with self.subTest(tz=tz):
                body = (
                    f'<FlexStatementResponse timestamp="28 August, 2012 10:37 AM {tz}">'
                    '<Status>Success</Status>'
                    '<ReferenceCode>0</ReferenceCode>'
                    '<Url>http://example.com</Url>'
                    '</FlexStatementResponse>'
                )
                out = client.parse_stmt_response(make_mock_response(body))
                self.assertEqual(
                    out.timestamp.utcoffset(),
                    datetime.timedelta(hours=hours),
                )

    def test_garbage_raises_bad_response(self):
        with self.assertRaises(client.BadResponseError):
            client.parse_stmt_response(make_mock_response("not xml"))

    def test_unexpected_root_raises_bad_response(self):
        body = '<UnexpectedRoot timestamp="28 August, 2012 10:37 AM EDT" />'
        with self.assertRaises(client.BadResponseError):
            client.parse_stmt_response(make_mock_response(body))


class CheckStatementResponseTestCase(unittest.TestCase):
    """Coverage for every branch in check_statement_response."""

    def test_flex_query_response_returns_true(self):
        resp = make_mock_response(FLEX_QUERY_RESPONSE)
        self.assertIs(client.check_statement_response(resp), True)

    def test_server_busy_returns_5(self):
        body = (
            '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM EDT">'
            '<Status>Warn</Status>'
            '<ErrorCode>1009</ErrorCode>'
            '<ErrorMessage>Heavy load.</ErrorMessage>'
            '</FlexStatementResponse>'
        )
        self.assertEqual(client.check_statement_response(make_mock_response(body)), 5)

    def test_generation_in_progress_returns_5(self):
        body = (
            '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM EDT">'
            '<Status>Warn</Status>'
            '<ErrorCode>1019</ErrorCode>'
            '<ErrorMessage>Generation in progress.</ErrorMessage>'
            '</FlexStatementResponse>'
        )
        self.assertEqual(client.check_statement_response(make_mock_response(body)), 5)

    def test_throttled_returns_10(self):
        body = (
            '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM EDT">'
            '<Status>Warn</Status>'
            '<ErrorCode>1018</ErrorCode>'
            '<ErrorMessage>Too many requests.</ErrorMessage>'
            '</FlexStatementResponse>'
        )
        self.assertEqual(client.check_statement_response(make_mock_response(body)), 10)

    def test_other_error_raises_response_code_error(self):
        with self.assertRaises(client.ResponseCodeError) as cm:
            client.check_statement_response(make_mock_response(RESPONSE_FAIL))
        self.assertEqual(cm.exception.code, "1012")
        self.assertIn("Token has expired", cm.exception.msg)

    def test_garbage_raises_bad_response(self):
        with self.assertRaises(client.BadResponseError):
            client.check_statement_response(make_mock_response("not xml at all"))

    def test_malformed_flex_statement_response_raises_bad(self):
        body = '<FlexStatementResponse>missing required fields</FlexStatementResponse>'
        with self.assertRaises(client.BadResponseError):
            client.check_statement_response(make_mock_response(body))


class RequestStatementErrorPathTestCase(unittest.TestCase):
    """When the statement-request endpoint returns a Fail status,
    request_statement raises ResponseCodeError."""

    @patch("requests.get")
    def test_request_statement_raises_on_fail(self, mock_get):
        mock_get.return_value = make_mock_response(RESPONSE_FAIL)
        with self.assertRaises(client.ResponseCodeError) as cm:
            client.request_statement(token="DEADBEEF", query_id="0987654321")
        self.assertEqual(cm.exception.code, "1012")


class DownloadTimeoutTestCase(unittest.TestCase):
    """Download bails with StatementGenerationTimeout when the server keeps
    saying 'try again' beyond max_tries."""

    @patch("time.sleep")  # don't actually sleep
    @patch("requests.get")
    def test_max_tries_exceeded(self, mock_get, _mock_sleep):
        # First request: SendRequest returns success (gives us a reference code).
        # Subsequent requests: GetStatement returns SERVER_BUSY indefinitely.
        busy = (
            '<FlexStatementResponse timestamp="28 August, 2012 10:37 AM EDT">'
            '<Status>Warn</Status><ErrorCode>1009</ErrorCode>'
            '<ErrorMessage>Heavy load.</ErrorMessage></FlexStatementResponse>'
        )
        responses = [make_mock_response(RESPONSE_SUCCESS)] + [
            make_mock_response(busy)
        ] * 20
        mock_get.side_effect = responses

        with self.assertRaises(client.StatementGenerationTimeout):
            client.download("DEADBEEF", "0987654321", max_tries=3)


class LazyRequestsImportTestCase(unittest.TestCase):
    """Importing ibflex must not require `requests`. The lazy `_requests()`
    helper raises a clear ImportError when called without it installed."""

    def test_helper_returns_module_when_available(self):
        self.assertIs(client._requests(), requests)

    def test_helper_raises_clear_error_when_missing(self):
        import builtins
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("No module named 'requests'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=fake_import):
            with self.assertRaises(ImportError) as cm:
                client._requests()
            self.assertIn("ibflex2[web]", str(cm.exception))


class ExceptionConstructorTestCase(unittest.TestCase):
    """Exception subclasses store and expose their fields."""

    def test_response_code_error_fields(self):
        err = client.ResponseCodeError("1234", "boom")
        self.assertEqual(err.code, "1234")
        self.assertEqual(err.msg, "boom")
        self.assertIn("1234", str(err))
        self.assertIn("boom", str(err))

    def test_bad_response_error_holds_response(self):
        resp = make_mock_response("garbage")
        err = client.BadResponseError(response=resp)
        self.assertIs(err.response, resp)


class MainCliTestCase(unittest.TestCase):
    """The flexget CLI entrypoint round-trips through download() and prints."""

    @patch("builtins.print")
    @patch("ibflex.client.download")
    def test_main_prints_decoded_statement(self, mock_download, mock_print):
        mock_download.return_value = b"<xml-blob/>"
        with patch("sys.argv", ["flexget", "-t", "TOKEN", "-q", "QUERY"]):
            client.main()
        mock_download.assert_called_once_with("TOKEN", "QUERY")
        mock_print.assert_called_once_with("<xml-blob/>")


if __name__ == '__main__':
    unittest.main(verbosity=3)
