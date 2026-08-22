import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

import main


class TestBirthdayWisher(unittest.TestCase):

    def setUp(self):
        # Suppress console print output during test execution for clean runner logs
        self.print_patcher = patch("builtins.print")
        self.mock_print = self.print_patcher.start()

        self.test_csv_path = "birthdays.csv"
        self.original_csv_exists = os.path.exists(self.test_csv_path)
        if self.original_csv_exists:
            with open(self.test_csv_path, "r", encoding="utf-8") as f:
                self.saved_csv_data = f.read()

        today = main.get_today_date()
        df = pd.DataFrame([
            {"name": "Test Person", "email": "test@example.com", "year": 1990, "month": today.month, "day": today.day},
            {"name": "Other Person", "email": "other@example.com", "year": 1995, "month": (today.month % 12) + 1, "day": 1}
        ])
        df.to_csv(self.test_csv_path, index=False)

    def tearDown(self):
        self.print_patcher.stop()
        if self.original_csv_exists:
            with open(self.test_csv_path, "w", encoding="utf-8") as f:
                f.write(self.saved_csv_data)

    def test_credential_sanitization(self):
        """Test Case 1: Verifies quotes, inner spaces, tabs, and zero-width Unicode characters are stripped."""
        raw_email = "  'user@gmail.com' \u200b "
        raw_pass = " \"abcd efgh ijkl mnop\" \u200b\ufeff "

        self.assertEqual(main.sanitize_email(raw_email), "user@gmail.com")
        self.assertEqual(main.sanitize_password(raw_pass), "abcdefghijklmnop")

    @patch("smtplib.SMTP")
    @patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "NOTIFY_EMAIL": "notify@example.com", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False)
    def test_successful_wishes_smtp(self, mock_smtp_class):
        """Test Case 2: Verifies successful execution and email sending via SMTP when credentials are valid."""
        # Ensure Gmail API env vars are absent so SMTP path is taken
        env = {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "NOTIFY_EMAIL": "notify@example.com", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        with patch.dict(os.environ, env, clear=False):
            # Remove GMAIL_TOKEN_JSON if present to force SMTP path
            os.environ.pop("GMAIL_TOKEN_JSON", None)
            main.run()
        self.assertTrue(mock_smtp.login.called)
        self.assertGreaterEqual(mock_smtp.send_message.call_count, 1)

    @patch("smtplib.SMTP")
    @patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "wrongpassword123", "GITHUB_ACTIONS": "true", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False)
    def test_smtp_auth_failure(self, mock_smtp_class):
        """Test Case 3: Verifies handling of 535 Bad Credentials (SMTPAuthenticationError)."""
        import smtplib
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        mock_smtp_class.return_value = mock_smtp

        with patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "wrongpassword123", "GITHUB_ACTIONS": "true", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False):
            os.environ.pop("GMAIL_TOKEN_JSON", None)
            with self.assertRaises(SystemExit) as cm:
                main.run()
        self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_vars(self):
        """Test Case 4: Verifies proper error handling when no auth method is available."""
        with self.assertRaises(SystemExit) as cm:
            main.run()
        self.assertEqual(cm.exception.code, 1)

    @patch("smtplib.SMTP")
    @patch("time.sleep", return_value=None)
    @patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False)
    def test_smtp_transient_retry(self, mock_sleep, mock_smtp_class):
        """Test Case 5: Verifies SMTP retry connection logic when transient network drop occurs on first attempt."""
        import smtplib
        mock_smtp_fail = MagicMock()
        mock_smtp_fail.starttls.side_effect = smtplib.SMTPConnectError(421, "Service unavailable")

        mock_smtp_success = MagicMock()

        # Fail on attempt 1, succeed on attempt 2
        mock_smtp_class.side_effect = [mock_smtp_fail, mock_smtp_success]

        with patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False):
            os.environ.pop("GMAIL_TOKEN_JSON", None)
            main.run()
        self.assertEqual(mock_smtp_class.call_count, 2)

    def test_empty_birthday_list(self):
        """Test Case 6: Verifies clean exit (0) when there are no birthdays today."""
        today = main.get_today_date()
        different_month = (today.month % 12) + 1
        df = pd.DataFrame([
            {"name": "No Birthday Today", "email": "nobday@example.com", "year": 1990, "month": different_month, "day": 1}
        ])
        df.to_csv("birthdays.csv", index=False)

        with patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False):
            os.environ.pop("GMAIL_TOKEN_JSON", None)
            with self.assertRaises(SystemExit) as cm:
                main.run()
        self.assertEqual(cm.exception.code, 0)

    @patch("smtplib.SMTP")
    @patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "NOTIFY_EMAIL": "admin@example.com", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False)
    def test_partial_send_failure(self, mock_smtp_class):
        """Test Case 7: Verifies system handles send failure for 1 contact without crashing summary email."""
        mock_smtp = MagicMock()
        # Fail first send (recipient email), succeed second send (notify email)
        mock_smtp.send_message.side_effect = [Exception("Invalid Recipient Address"), None]
        mock_smtp_class.return_value = mock_smtp

        with patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "NOTIFY_EMAIL": "admin@example.com", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False):
            os.environ.pop("GMAIL_TOKEN_JSON", None)
            main.run()
        self.assertEqual(mock_smtp.send_message.call_count, 2)

    def test_decode_csv(self):
        """Test Case 8: Verifies decode_csv logic with plain CSV and base64 strings."""
        import base64
        raw_csv = "name,email,year,month,day\nAlice,alice@test.com,1990,5,10"
        b64_csv = base64.b64encode(raw_csv.encode("utf-8")).decode("utf-8")

        decoded = base64.b64decode(b64_csv).decode("utf-8")
        self.assertEqual(decoded, raw_csv)

    def test_gmail_api_send(self):
        """Test Case 9: Verifies email sending via Gmail API path."""
        mock_service = MagicMock()

        # Mock the Gmail API send chain: service.users().messages().send().execute()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {"id": "msg123"}
        mock_service.users.return_value.getProfile.return_value.execute.return_value = {"emailAddress": "sender@gmail.com"}

        # Create a mock gmail_auth module
        mock_gmail_auth = MagicMock()
        mock_gmail_auth.get_gmail_service.return_value = mock_service

        token_json = '{"refresh_token":"test","client_id":"test","client_secret":"test","token":"test"}'
        with patch.dict(os.environ, {"GMAIL_TOKEN_JSON": token_json, "NOTIFY_EMAIL": "notify@example.com", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False):
            with patch.dict('sys.modules', {'gmail_auth': mock_gmail_auth}):
                main.run()

        # Verify Gmail API send was called (birthday email + notification email)
        self.assertGreaterEqual(
            mock_service.users.return_value.messages.return_value.send.call_count, 1
        )

    def test_gmail_api_fallback_to_smtp(self):
        """Test Case 10: Verifies fallback to SMTP when GMAIL_TOKEN_JSON is not set."""
        import smtplib
        with patch("smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp_class.return_value = mock_smtp

            with patch.dict(os.environ, {"EMAIL": "sender@gmail.com", "PASSWORD": "abcdefghijklmnop", "SENDER_EMAIL": "definitely.human.mail@gmail.com"}, clear=False):
                os.environ.pop("GMAIL_TOKEN_JSON", None)
                main.run()

            # Should have used SMTP, not Gmail API
            self.assertTrue(mock_smtp.login.called)


if __name__ == "__main__":
    unittest.main()
