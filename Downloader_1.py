from datetime import datetime, timedelta
import calendar

# --- Original Logic (Where the error occurred) ---
# Assuming this is inside a loop or function where `year` and `month_num` are defined:
# day_in_month = datetime(year, month_num, 1).days_in_month # <--- THIS CAUSES THE ERROR

# --- FIX 1: Using the `calendar` module (Recommended for simplicity) ---
# Get the number of days in the month using the standard library
def get_days_in_month_calendar(year, month_num):
    """Uses the standard calendar library to find the number of days."""
    # calendar.monthrange returns (weekday_of_first_day, number_of_days)
    _, days_in_month = calendar.monthrange(year, month_num)
    return days_in_month

# Example Usage:
year = 2024
month_num = 10 # October
days_in_month_fixed = get_days_in_month_calendar(year, month_num)

print(f"Using calendar module: October {year} has {days_in_month_fixed} days.")
# Output: Using calendar module: October 2024 has 31 days.


# --- FIX 2: Using standard `datetime` and `timedelta` (Good alternative) ---
# This technique calculates the first day of the next month and subtracts the first day of the current month
def get_days_in_month_timedelta(year, month_num):
    """Calculates the number of days using date arithmetic."""
    current_month_start = datetime(year, month_num, 1)
    
    # Calculate the start of the next month
    if month_num == 12:
        next_month_start = datetime(year + 1, 1, 1)
    else:
        next_month_start = datetime(year, month_num + 1, 1)

    # Days in month is the difference (as timedelta) divided by one day
    # We use `.days` attribute of the timedelta object
    days_in_month = (next_month_start - current_month_start).days
    return days_in_month

# Example Usage:
year = 2024
month_num = 10 # October
days_in_month_fixed_2 = get_days_in_month_timedelta(year, month_num)

print(f"Using timedelta logic: October {year} has {days_in_month_fixed_2} days.")
# Output: Using timedelta logic: October 2024 has 31 days.


# --- How to implement in your script ---
# If your goal was just to get the number of days:
# Replace the line:
# day_in_month = datetime(year, month_num, 1).days_in_month
#
# With:
# import calendar # Make sure to add this import at the top of Downloader_1.py
# day_in_month = calendar.monthrange(year, month_num)[1]