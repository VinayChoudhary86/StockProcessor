using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Windows.Forms;
using System.Net;

// When price declines but no change in OI that is an alarm
namespace ShareUpdates
{

    public partial class NSEData : Form
    {
        string[] indexNames = { "NIFTY", "BANKNIFTY" };
        string[] shares = { "DIXON", "TATAMOTORS", "TCS", "INFY", "RELIANCE", "INDUSINDBK", "RVNL", "DABUR", "TATASTEEL", "SBIN", "AXISBANK", "BANKBARODA" };
        Dictionary<int, string[]> expiryDates = new Dictionary<int, string[]>();
        string[] filesDownloaded = { };
        public NSEData()
        {
            LoadExpiryDates();
            InitializeComponent();
            DateFrom.Value = new DateTime(2021, 01, 01);
            DateTo.Value = new DateTime(2021, 06, 30);
        }

        private void DownloadDataFromNSE()
        {
            bool isScripDataDownloaded = false;
            string scrip = string.Empty;//Convert.ToString(comboBox1.SelectedItem);
            //List<string> scripsToDownload = SharesList.Items;
            int selectedSharesCount = SharesList.SelectedItems.Count;
            if (selectedSharesCount != 0 || chkBankNifty.Checked || chkNifty.Checked)
            {
                if (chkBankNifty.Checked)
                {
                    DownloadCSV(ref isScripDataDownloaded, 0, "BANKNIFTY");
                }
                else if (chkNifty.Checked)
                {
                    DownloadCSV(ref isScripDataDownloaded, 0, "NIFTY");
                }
                else
                {
                    for (int i = 0; i <= selectedSharesCount - 1; i++)
                    {
                        DownloadCSV(ref isScripDataDownloaded, i, scrip);
                    }
                }

                if (!isScripDataDownloaded)
                {
                    MessageBox.Show("No Scrip data to be downloaded", "No data to be downloaded", MessageBoxButtons.OK);
                }

                
            }
            else
            {
                MessageBox.Show("Please select a Share to download", "Select a Share", MessageBoxButtons.OK);
            }
        }

        private void DownloadCSV(ref bool isScripDataDownloaded, int i, string scrip)
        {
            DateTime dateTimeFrom = DateFrom.Value;
            DateTime dateTimeTo = DateTo.Value;

            if (string.IsNullOrEmpty(scrip))
            {
                scrip = Convert.ToString(SharesList.SelectedItems[i]);
            }

            // ---------------------------------------------------------
            // *** UPDATED CODE: YEAR-WISE DELIVERY DATA DOWNLOAD ***
            // ---------------------------------------------------------

            DateTime chunkStart = dateTimeFrom;

            while (chunkStart <= dateTimeTo)
            {
                // End of this chunk = 31-Dec of the year
                DateTime chunkEnd = new DateTime(chunkStart.Year, 12, 31);

                // Do not exceed user-selected To date
                if (chunkEnd > dateTimeTo)
                    chunkEnd = dateTimeTo;

                // Delivery URL for this chunk
                string downloadDeliveryData =
                    "https://www.nseindia.com/api/historicalOR/generateSecurityWiseHistoricalData?" +
                    "from=" + chunkStart.ToString("dd-MM-yyyy") +
                    "&to=" + chunkEnd.ToString("dd-MM-yyyy") +
                    "&symbol=" + scrip +
                    "&type=priceVolumeDeliverable&series=EQ&csv=true";

                Process.Start(downloadDeliveryData);

                // Next chunk starts next day
                chunkStart = chunkEnd.AddDays(1);
            }

            // ---------------------------------------------------------
            // EXISTING CODE (UNCHANGED)
            // ---------------------------------------------------------

            bool isDataAvailable = false;
            TimeSpan start = new TimeSpan(21, 0, 0); //10 o'clock

            if (DateTime.Now.TimeOfDay > start)
            {
                isDataAvailable = true;
            }

            //Checks if data is available on NSE to downlaod
            if (dateTimeFrom.Date < DateTime.Now.Date ||
               (dateTimeFrom.Date == DateTime.Now.Date && isDataAvailable))
            {
                bool isDateTimeFromAWeekend = (dateTimeFrom.DayOfWeek == DayOfWeek.Saturday || dateTimeFrom.DayOfWeek == DayOfWeek.Sunday);
                bool isDateTimeToAWeekend = (dateTimeTo.DayOfWeek == DayOfWeek.Saturday || dateTimeTo.DayOfWeek == DayOfWeek.Sunday);
                int diffInDays = (dateTimeTo.Date - dateTimeFrom.Date).Days;

                if (scrip != "NIFTY" && scrip != "BANKNIFTY")
                {
                    DownloadEquityData(dateTimeFrom.ToString("dd-MM-yyyy"), dateTimeTo.ToString("dd-MM-yyyy"), scrip);
                }

                int monthFrom = getMonthIndex(dateTimeFrom);
                int monthTo = getMonthIndex(dateTimeTo);

                for (int month = monthFrom; month <= monthTo; month++)
                {
                    string dateFrom = string.Empty;
                    string toDate = string.Empty;
                    string expiryDate = string.Empty;

                    int year = Convert.ToInt32(expiryDates[month][2]);

                    dateFrom = "01-" + expiryDates[month][3] + "-" + year;
                    toDate = DateTime.DaysInMonth(year, Convert.ToInt32(expiryDates[month][3])) + "-" +
                             GetMonthIn2Digits(Convert.ToInt32(expiryDates[month][3])) + "-" + year;

                    expiryDate = expiryDates[month][0] + "-" + expiryDates[month][1] + "-" + year;
                    DownloadFuturesData(dateFrom, toDate, expiryDate, scrip);

                    expiryDate = expiryDates[month + 1][0] + "-" + expiryDates[month + 1][1] + "-" +
                                 Convert.ToInt32(expiryDates[month + 1][2]);
                    DownloadFuturesData(dateFrom, toDate, expiryDate, scrip);
                }

                isScripDataDownloaded = true;
            }
        }


        private void NSEData_Load(object sender, EventArgs e)
        {
            for (int i = 0; i <= shares.Length - 1; i++)
            {
                //comboBox1.Items.Add(shares[i]);
                SharesList.Items.Add(shares[i]);
            }
        }

        private static void DownloadFuturesData(string startDate, string endDate, string expiryDate, string scrip)
        {
            string downloadDerivate = string.Empty;
            //int monthNum = 
            if (scrip == "BANKNIFTY" || scrip == "NIFTY")
            {
                downloadDerivate = "https://nseindia.com/api/historical/fo/derivatives?&from=" + startDate + "&to=" + endDate + "&expiryDate=" + expiryDate + "&instrumentType=FUTIDX&symbol=" + scrip + "&csv=true";
            }
            else
            {
                downloadDerivate = "https://nseindia.com/api/historical/fo/derivatives?&from=" + startDate + "&to=" + endDate + "&expiryDate=" + expiryDate + "&instrumentType=FUTSTK&symbol=" + scrip + "&csv=true";
            }
            Process oMyProcess = Process.Start(downloadDerivate);
        }

        private static void DownloadEquityData(string startDate, string endDate, string scrip)
        {
            // Convert input strings to DateTime
            DateTime fromDate = DateTime.ParseExact(startDate, "dd-MM-yyyy", null);
            DateTime toDate = DateTime.ParseExact(endDate, "dd-MM-yyyy", null);

            DateTime chunkStart = fromDate;

            while (chunkStart <= toDate)
            {
                // End of current chunk = 31-Dec of that year
                DateTime chunkEnd = new DateTime(chunkStart.Year, 12, 31);

                // Clamp if beyond requested endDate
                if (chunkEnd > toDate)
                    chunkEnd = toDate;

                // Build the NSE equity API URL for this chunk
                string url =
                    "https://www.nseindia.com/api/historical/cm/equity?" +
                    "symbol=" + scrip +
                    "&series=[%22EQ%22]" +
                    "&from=" + chunkStart.ToString("dd-MM-yyyy") +
                    "&to=" + chunkEnd.ToString("dd-MM-yyyy") +
                    "&csv=false";

                // Fire download
                Process.Start(url);

                // Next chunk begins on next day
                chunkStart = chunkEnd.AddDays(1);
            }
        }


        private void DownloadAll_CheckedChanged(object sender, EventArgs e)
        {

            //int sharesCount = 0;
            for (int i = 0; i < SharesList.Items.Count; i++)
            {
                if (DownloadAll.Checked)
                {
                    SharesList.SetSelected(i, true);
                }
                else
                {
                    SharesList.SetSelected(i, false);
                }
            }

        }

        private static string GetMonthIn2Digits(int month)
        {
            if (1 <= month && month <= 9)
            {
                return string.Concat("0", month.ToString());
            }
            else
            {
                return month.ToString();
            }
        }

        private void DownloadData_Click(object sender, EventArgs e)
        {
            //https://youtu.be/2fbRrJq7WHc?t=779
            //https://www.nseindia.com/get-quotes/derivatives?symbol=TATAMOTORS                                 -- Derivative Data
            //https://www1.nseindia.com/products/content/equities/indices/historical_index_data.htm             -- Download Data
            //https://www.nseindia.com/api/snapshot-derivatives-equity?index=contracts&type=volume&csv=true     -- Download most Active contracts
            label3.Visible = true;
            progressBar1.Visible = true;
            DownloadDataFromNSE();
            //DownLoadOptionChain();
        }
        private void DownloadDelivery_Click(object sender, EventArgs e)
        {
            //https://www1.nseindia.com/archives/equities/mto/MTO
            //// https://www1.nseindia.com//content/historical/EQUITIES/2022/FEB/cm14FEB2022bhav.csv.zip

            // Download delivery data
            DateTime dateTimeFrom = DateFrom.Value;

            DateTime dateTimeTo = DateTo.Value;
            DateTime dateToDownload = dateTimeFrom;
            int days = (dateTimeTo - dateTimeFrom).Days + 1;


            for (int i = 1; i <= days; i++)
            {
                using (WebClient wc = new WebClient())
                {
                    string year = dateToDownload.Year.ToString();
                    string month = GetMonthIn2Digits(dateToDownload.Month);
                    string date = GetMonthIn2Digits(dateToDownload.Day);
                    string url = string.Concat("https://www1.nseindia.com/archives/equities/mto/MTO_", date, month, year, ".DAT");
                    Uri uri = new Uri(url);
                    string fileName = string.Concat("DELIVERYDATA_", date, month, year, ".csv");
                    wc.DownloadFileAsync(uri, fileName);
                    dateToDownload = dateToDownload.AddDays(1);
                }
            }

            // Download Bhav Copy
            dateTimeFrom = DateFrom.Value;

            dateTimeTo = DateTo.Value;
            dateToDownload = dateTimeFrom;
            days = (dateTimeTo - dateTimeFrom).Days + 1;

            for (int i = 1; i <= days; i++)
            {
                using (WebClient wc = new WebClient())
                {
                    string year = dateToDownload.Year.ToString();
                    string month = dateToDownload.ToString("MMM").ToUpper();
                    string date = GetMonthIn2Digits(dateToDownload.Day);
                    string url = string.Concat("https://www1.nseindia.com//content/historical/EQUITIES/", year, "/", month, "/cm", date, month, year, "bhav.csv.zip");
                    Uri uri = new Uri(url);
                    string fileName = string.Concat("bhavcopy_", date, month, year, ".zip");
                    wc.DownloadFileAsync(uri, fileName);
                    dateToDownload = dateToDownload.AddDays(1);
                }
            }

            MessageBox.Show("Data downloded successfully", "Data downloaded Successfully", MessageBoxButtons.OK);
        }

        private int getMonthIndex(DateTime date)
        {
            int index = 1;
            int month = 1;
            int year = 2018;

            while(true)
            {
                month++;
                if(month == 13)
                {
                    month =1;
                    year++;
                }
                index++;

                if (month == date.Month && year == date.Year)
                    break;
            }

            return index;
        }
        private void LoadExpiryDates()
        {

            // https://www1.nseindia.com/products/content/derivatives/equities/historical_fo.htm            -- Expiry Dates
            // https://www.nseindia.com/api/historicalOR/generateSecurityWiseHistoricalData?from=01-01-2025&to=01-11-2025&symbol=RELIANCE&type=priceVolumeDeliverable&series=EQ&csv=true                  -- Delivery

            expiryDates.Add(1, new string[] { "25", "Jan", "2018", "01" });
            expiryDates.Add(2, new string[] { "22", "Feb", "2018", "02" }); // Last Thursday is 22nd, 29th (2018 is not a leap year, Feb has 28 days)
            expiryDates.Add(3, new string[] { "28", "Mar", "2018", "03" }); // March 29th was a holiday (Mahavir Jayanti), so expiry moved to 28th
            expiryDates.Add(4, new string[] { "26", "Apr", "2018", "04" });
            expiryDates.Add(5, new string[] { "31", "May", "2018", "05" });
            expiryDates.Add(6, new string[] { "28", "Jun", "2018", "06" });
            expiryDates.Add(7, new string[] { "26", "Jul", "2018", "07" });
            expiryDates.Add(8, new string[] { "30", "Aug", "2018", "08" });
            expiryDates.Add(9, new string[] { "27", "Sep", "2018", "09" });
            expiryDates.Add(10, new string[] { "25", "Oct", "2018", "10" });
            expiryDates.Add(11, new string[] { "29", "Nov", "2018", "11" });
            expiryDates.Add(12, new string[] { "27", "Dec", "2018", "12" });

            expiryDates.Add(13, new string[] { "31", "Jan", "2019", "01" });
            expiryDates.Add(14, new string[] { "28", "Feb", "2019", "02" });
            expiryDates.Add(15, new string[] { "28", "Mar", "2019", "03" });
            expiryDates.Add(16, new string[] { "25", "Apr", "2019", "04" });
            expiryDates.Add(17, new string[] { "30", "May", "2019", "05" });
            expiryDates.Add(18, new string[] { "27", "Jun", "2019", "06" });
            expiryDates.Add(19, new string[] { "25", "Jul", "2019", "07" });
            expiryDates.Add(20, new string[] { "29", "Aug", "2019", "08" });
            expiryDates.Add(21, new string[] { "26", "Sep", "2019", "09" });
            expiryDates.Add(22, new string[] { "31", "Oct", "2019", "10" });
            expiryDates.Add(23, new string[] { "28", "Nov", "2019", "11" });
            expiryDates.Add(24, new string[] { "26", "Dec", "2019", "12" });

            expiryDates.Add(25, new string[] { "30", "Jan", "2020", "01" });
            expiryDates.Add(26, new string[] { "27", "Feb", "2020", "02" });
            expiryDates.Add(27, new string[] { "26", "Mar", "2020", "03" });
            expiryDates.Add(28, new string[] { "30", "Apr", "2020", "04" });
            expiryDates.Add(29, new string[] { "28", "May", "2020", "05" });
            expiryDates.Add(30, new string[] { "25", "Jun", "2020", "06" });
            expiryDates.Add(31, new string[] { "30", "Jul", "2020", "07" });
            expiryDates.Add(32, new string[] { "27", "Aug", "2020", "08" });
            expiryDates.Add(33, new string[] { "24", "Sep", "2020", "09" });
            expiryDates.Add(34, new string[] { "29", "Oct", "2020", "10" });
            expiryDates.Add(35, new string[] { "26", "Nov", "2020", "11" });
            expiryDates.Add(36, new string[] { "31", "Dec", "2020", "12" });

            // 2021 Expiry Dates
            expiryDates.Add(37, new string[] { "28", "Jan", "2021", "01" });
            expiryDates.Add(38, new string[] { "25", "Feb", "2021", "02" });
            expiryDates.Add(39, new string[] { "25", "Mar", "2021", "03" });
            expiryDates.Add(40, new string[] { "29", "Apr", "2021", "04" });
            expiryDates.Add(41, new string[] { "27", "May", "2021", "05" });
            expiryDates.Add(42, new string[] { "24", "Jun", "2021", "06" });
            expiryDates.Add(43, new string[] { "29", "Jul", "2021", "07" });
            expiryDates.Add(44, new string[] { "26", "Aug", "2021", "08" });
            expiryDates.Add(45, new string[] { "30", "Sep", "2021", "09" });
            expiryDates.Add(46, new string[] { "28", "Oct", "2021", "10" });
            expiryDates.Add(47, new string[] { "25", "Nov", "2021", "11" });
            expiryDates.Add(48, new string[] { "30", "Dec", "2021", "12" });

            // 2022 Expiry Dates
            expiryDates.Add(49, new string[] { "27", "Jan", "2022", "01" });
            expiryDates.Add(50, new string[] { "24", "Feb", "2022", "02" });
            expiryDates.Add(51, new string[] { "31", "Mar", "2022", "03" });
            expiryDates.Add(52, new string[] { "28", "Apr", "2022", "04" });
            expiryDates.Add(53, new string[] { "26", "May", "2022", "05" });
            expiryDates.Add(54, new string[] { "30", "Jun", "2022", "06" });
            expiryDates.Add(55, new string[] { "28", "Jul", "2022", "07" });
            expiryDates.Add(56, new string[] { "25", "Aug", "2022", "08" });
            expiryDates.Add(57, new string[] { "29", "Sep", "2022", "09" });
            expiryDates.Add(58, new string[] { "27", "Oct", "2022", "10" });
            expiryDates.Add(59, new string[] { "24", "Nov", "2022", "11" });
            expiryDates.Add(60, new string[] { "29", "Dec", "2022", "12" });

            // 2023 Expiry Dates
            expiryDates.Add(61, new string[] { "26", "Jan", "2023", "01" });
            expiryDates.Add(62, new string[] { "23", "Feb", "2023", "02" });
            expiryDates.Add(63, new string[] { "30", "Mar", "2023", "03" });
            expiryDates.Add(64, new string[] { "27", "Apr", "2023", "04" });
            expiryDates.Add(65, new string[] { "25", "May", "2023", "05" });
            expiryDates.Add(66, new string[] { "29", "Jun", "2023", "06" });
            expiryDates.Add(67, new string[] { "27", "Jul", "2023", "07" });
            expiryDates.Add(68, new string[] { "31", "Aug", "2023", "08" });
            expiryDates.Add(69, new string[] { "28", "Sep", "2023", "09" });
            expiryDates.Add(70, new string[] { "26", "Oct", "2023", "10" });
            expiryDates.Add(71, new string[] { "30", "Nov", "2023", "11" });
            expiryDates.Add(72, new string[] { "28", "Dec", "2023", "12" });

            // 2024 Expiry Dates
            expiryDates.Add(73, new string[] { "25", "Jan", "2024", "01" });
            expiryDates.Add(74, new string[] { "29", "Feb", "2024", "02" });
            expiryDates.Add(75, new string[] { "28", "Mar", "2024", "03" });
            expiryDates.Add(76, new string[] { "25", "Apr", "2024", "04" });
            expiryDates.Add(77, new string[] { "30", "May", "2024", "05" });
            expiryDates.Add(78, new string[] { "27", "Jun", "2024", "06" });
            expiryDates.Add(79, new string[] { "25", "Jul", "2024", "07" });
            expiryDates.Add(80, new string[] { "29", "Aug", "2024", "08" });
            expiryDates.Add(81, new string[] { "26", "Sep", "2024", "09" });
            expiryDates.Add(82, new string[] { "31", "Oct", "2024", "10" });
            expiryDates.Add(83, new string[] { "28", "Nov", "2024", "11" });
            expiryDates.Add(84, new string[] { "26", "Dec", "2024", "12" });

            // 2025 Expiry Dates
            expiryDates.Add(85, new string[] { "30", "Jan", "2025", "01" });
            expiryDates.Add(86, new string[] { "27", "Feb", "2025", "02" });
            expiryDates.Add(87, new string[] { "27", "Mar", "2025", "03" });
            expiryDates.Add(88, new string[] { "24", "Apr", "2025", "04" });
            expiryDates.Add(89, new string[] { "29", "May", "2025", "05" });
            expiryDates.Add(90, new string[] { "26", "Jun", "2025", "06" });
            expiryDates.Add(91, new string[] { "31", "Jul", "2025", "07" });
            expiryDates.Add(92, new string[] { "28", "Aug", "2025", "08" });
            expiryDates.Add(93, new string[] { "25", "Sep", "2025", "09" });
            expiryDates.Add(94, new string[] { "30", "Oct", "2025", "10" });
            expiryDates.Add(95, new string[] { "27", "Nov", "2025", "11" });
            expiryDates.Add(96, new string[] { "25", "Dec", "2025", "12" });

            // 2026 Expiry Dates
            expiryDates.Add(97, new string[] { "29", "Jan", "2026", "01" });
            expiryDates.Add(98, new string[] { "26", "Feb", "2026", "02" });
            expiryDates.Add(99, new string[] { "26", "Mar", "2026", "03" });
            expiryDates.Add(100, new string[] { "30", "Apr", "2026", "04" });
            expiryDates.Add(101, new string[] { "28", "May", "2026", "05" });
            expiryDates.Add(102, new string[] { "25", "Jun", "2026", "06" });
            expiryDates.Add(103, new string[] { "30", "Jul", "2026", "07" });
            expiryDates.Add(104, new string[] { "27", "Aug", "2026", "08" });
            expiryDates.Add(105, new string[] { "24", "Sep", "2026", "09" });
            expiryDates.Add(106, new string[] { "29", "Oct", "2026", "10" });
            expiryDates.Add(107, new string[] { "26", "Nov", "2026", "11" });
            expiryDates.Add(108, new string[] { "31", "Dec", "2026", "12" });
        }
    }
}
