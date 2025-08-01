# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import re
import unittest

from src.logstory.main import datetime_to_filetime, filetime_to_datetime


class TestFiletimeConversions(unittest.TestCase):
  """Test cases for Windows File Time conversion functions."""

  def test_lastlogon_winfiletime_regex(self):
    """Test the lastLogonWinFileTime regex pattern extraction."""
    # Sample data with lastLogon field
    input_str = (
        r'"BadLogonCount":1,"badPasswordTime":133505027883351005,"badPwdCount":1,"CannotChangePassword":false,"CanonicalName":"lunarstiiiness.com/Users/Stan'
        r' Conrad","Certificates":[],"City":null,"CN":"Stan'
        r' Conrad","codePage":0,"Company":null,"CompoundIdentitySupported":[],"Country":null,"countryCode":0,"Created":"\/Date(1705615749000)\/","createTimeStamp":"\/Date(1705615749000)\/","Deleted":null,"Department":null,"Description":null,"DisplayName":"Stan'
        r' Conrad","Division":null,"DoesNotRequirePreAuth":false,"dSCorePropagationData":["\/Date(1705950883000)\/","\/Date(1705950882000)\/","\/Date(1705950881000)\/","\/Date(1705950880000)\/","\/Date(-11627630591000)\/"],"EmailAddress":"stan.conrad@lunarstiiiness.com","EmployeeID":null,"EmployeeNumber":null,"Fax":null,"garbageCollPeriod":1209600,"HomeDirectory":null,"HomedirRequired":false,"HomeDrive":null,"homeMDB":"CN=Mailbox'
        r" Database 0026588973,CN=Databases,CN=Exchange Administrative Group"
        r" (FYDIBOHF23SPDLT),CN=Administrative Groups,CN=lunarstiiiness,CN=Microsoft"
        r' Exchange,CN=Services,CN=Configuration,DC=lunarstiiiness,DC=com","HomePage":null,"HomePhone":null,"Initials":null,"instanceType":4,"internetEncoding":0,"isDeleted":null,"KerberosEncryptionType":[],"LastBadPasswordAttempt":"\/Date(1706029188335)\/","LastKnownParent":null,"lastLogoff":0,"lastLogon":133504425386052066,"LastLogonDate":"\/Date(1705616525382)\/","lastLogonTimestamp":133500901253824436,'
    )

    # The regex pattern from the YAML config
    pattern = r'("lastLogon":)(\d{18})(,)'

    # Test that the pattern matches and extracts the correct filetime value
    match = re.search(pattern, input_str)
    self.assertIsNotNone(match, "Pattern should match the lastLogon field")

    # Group 2 should contain the 18-digit filetime value
    filetime_str = match.group(2)
    self.assertEqual(filetime_str, "133504425386052066")
    self.assertEqual(len(filetime_str), 18, "Windows filetime should be 18 digits")

    # Verify it's a valid integer
    filetime_int = int(filetime_str)
    self.assertIsInstance(filetime_int, int)
    self.assertGreater(filetime_int, 0)

  def test_filetime_to_datetime_known_values(self):
    """Test filetime_to_datetime with known values."""
    # Test case 1: Known Windows filetime value
    # 133504425386052066 corresponds to approximately 2024-01-19 01:02:18.605 UTC
    filetime = 133504425386052066
    result = filetime_to_datetime(filetime)

    self.assertIsInstance(result, datetime.datetime)
    self.assertEqual(result.tzinfo, datetime.UTC)

    # Verify the conversion is approximately correct (within a few seconds)
    expected_year = 2024
    expected_month = 1
    self.assertEqual(result.year, expected_year)
    self.assertEqual(result.month, expected_month)

    # Test case 2: Windows epoch (Jan 1, 1601)
    windows_epoch = 0
    result_epoch = filetime_to_datetime(windows_epoch)
    self.assertEqual(result_epoch.year, 1601)
    self.assertEqual(result_epoch.month, 1)
    self.assertEqual(result_epoch.day, 1)

  def test_datetime_to_filetime_known_values(self):
    """Test datetime_to_filetime with known values."""
    # Test case 1: Use the actual filetime value from the sample data
    # First convert the known filetime to see what datetime it represents
    known_filetime = 133504425386052066
    actual_dt = filetime_to_datetime(known_filetime)

    # Now convert back to filetime - should match exactly
    result = datetime_to_filetime(actual_dt)

    self.assertIsInstance(result, int)
    self.assertGreater(result, 0)

    # The result should match our known filetime value within a small tolerance
    # (allowing for precision differences in microsecond conversion)
    self.assertAlmostEqual(result, known_filetime, delta=10)

    # Test case 2: Unix epoch (Jan 1, 1970)
    unix_epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
    result_unix = datetime_to_filetime(unix_epoch)
    # Unix epoch in Windows filetime should equal EPOCH_AS_FILETIME
    from src.logstory.main import EPOCH_AS_FILETIME

    self.assertEqual(result_unix, EPOCH_AS_FILETIME)

  def test_filetime_conversion_round_trip(self):
    """Test that converting datetime -> filetime -> datetime preserves the value."""
    # Test with current time
    original_dt = datetime.datetime.now(datetime.UTC)

    # Round trip: datetime -> filetime -> datetime
    filetime = datetime_to_filetime(original_dt)
    converted_dt = filetime_to_datetime(filetime)

    # Should be very close (within microseconds due to precision)
    time_diff = abs((converted_dt - original_dt).total_seconds())
    self.assertLess(
        time_diff, 0.001, "Round trip conversion should preserve datetime within 1ms"
    )

    # Test with specific historical date
    historical_dt = datetime.datetime(
        2020, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC
    )
    filetime2 = datetime_to_filetime(historical_dt)
    converted_dt2 = filetime_to_datetime(filetime2)

    time_diff2 = abs((converted_dt2 - historical_dt).total_seconds())
    self.assertLess(time_diff2, 0.001, "Round trip should work for historical dates")

  def test_filetime_conversion_edge_cases(self):
    """Test edge cases for filetime conversions."""
    # Test Windows epoch
    windows_epoch_dt = datetime.datetime(1601, 1, 1, tzinfo=datetime.UTC)
    filetime_epoch = datetime_to_filetime(windows_epoch_dt)
    self.assertEqual(filetime_epoch, 0)

    # Test that filetime 0 converts back to Windows epoch
    converted_back = filetime_to_datetime(0)
    self.assertEqual(converted_back.year, 1601)
    self.assertEqual(converted_back.month, 1)
    self.assertEqual(converted_back.day, 1)

  def test_windows_filetime_timestamp_processing(self):
    """Test that Windows FileTime timestamps are properly processed in logs."""
    # Import the _update_timestamp function
    from src.logstory.main import _update_timestamp

    # Sample log line with Windows FileTime
    log_text = '"lastLogon":133504425386052066,"LastLogonDate":"/Date(1705616525382)/"'

    # Timestamp configuration for lastLogonWinFileTime
    timestamp_config = {
        "name": "lastLogonWinFileTime",
        "dateformat": "filetime",
        "group": 2,
        "pattern": r'("lastLogon":)(\d{18})(,)',
    }

    # Create a base time and delta dict
    # Use the actual datetime from the filetime conversion to ensure exact match
    original_filetime = 133504425386052066
    old_base_time = filetime_to_datetime(original_filetime)
    ts_delta_dict = {"d": 1}  # 1 day ago

    # Process the timestamp
    updated_log = _update_timestamp(
        log_text, timestamp_config, old_base_time, ts_delta_dict
    )

    # Extract the new filetime from the updated log
    import re

    match = re.search(r'"lastLogon":(\d{18}),', updated_log)
    self.assertIsNotNone(match, "Updated log should contain a filetime")

    new_filetime = int(match.group(1))

    # Convert to datetime to verify the result
    new_dt = filetime_to_datetime(new_filetime)
    original_dt = filetime_to_datetime(133504425386052066)

    # The new datetime should be the same time on the day that is (today - 1 day)
    # Since old_base_time is the same as original_dt, and ts_delta_dict is {"d": 1},
    # the new timestamp should be (current_date - 1 day) with the same time as original
    current_date = datetime.datetime.now(datetime.UTC).date()
    expected_date = current_date - datetime.timedelta(days=1)

    # Check that the date was updated correctly
    self.assertEqual(
        new_dt.date(), expected_date, "Date should be updated to 1 day ago"
    )

    # Check that the time portion is preserved
    self.assertEqual(
        new_dt.time(), original_dt.time(), "Time portion should be preserved"
    )

  def test_epoch_dateformat_handling(self):
    """Test that dateformat: 'epoch' works correctly."""
    from src.logstory.main import _update_timestamp

    # Sample log line with Unix epoch timestamp
    log_text = '"creationTime": 1705615749, "expirationTime": 1705702149'

    # Timestamp configuration using dateformat: 'epoch'
    timestamp_config = {
        "name": "creationTime",
        "dateformat": "epoch",
        "group": 2,
        "pattern": r'("creationTime":\s*)(\d{10})',
    }

    # Create a base time from the epoch timestamp
    original_epoch = 1705615749
    old_base_time = datetime.datetime.fromtimestamp(original_epoch)
    ts_delta_dict = {"d": 7}  # 7 days ago

    # Process the timestamp
    updated_log = _update_timestamp(
        log_text, timestamp_config, old_base_time, ts_delta_dict
    )

    # Extract the new epoch timestamp
    import re

    match = re.search(r'"creationTime":\s*(\d{10})', updated_log)
    self.assertIsNotNone(match, "Updated log should contain an epoch timestamp")

    new_epoch = int(match.group(1))
    new_dt = datetime.datetime.fromtimestamp(new_epoch)

    # The new datetime should be approximately 7 days ago
    current_date = datetime.datetime.now(datetime.UTC).date()
    expected_date = current_date - datetime.timedelta(days=7)

    self.assertEqual(
        new_dt.date(), expected_date, "Date should be updated to 7 days ago"
    )


if __name__ == "__main__":
  unittest.main()
