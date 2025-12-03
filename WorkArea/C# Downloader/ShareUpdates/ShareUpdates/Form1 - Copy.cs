using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using System.Configuration;
using System.Windows.Forms.DataVisualization.Charting;

// When price declines but no change in OI that is an alarm
namespace ShareUpdates
{
    //public class HttpRequestHandler {
    //    private CookieContainer cookies;
    //    public HttpRequestHandler()
    //    {
    //        cookies = new CookieContainer();
    //    }
    //    public HttpWebRequest GenerateWebRequest(string url)
    //    {
    //        HttpWebRequest request = (HttpWebRequest)WebRequest.Create(new System.Uri(url));

    //        request.CookieContainer = cookies;
    //        request.AllowAutoRedirect = true;
    //        request.KeepAlive = true;
    //        request.Referer = HttpUtility.UrlEncode(referer);
    //        request.UserAgent = "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.8) Gecko/2009021910 Firefox/3.0.7 (.NET CLR 3.5.30729)";
    //        request.Headers.Add("Pragma", "no-cache");
    //        request.Timeout = 40000;

    //        return request;
    //    }
    //}

    public partial class NSEData : Form
    {
        string[] shares = { "AARTIIND", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "ALKEM", "AMARAJABAT", "AMBUJACEM", "APLLTD", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CADILAHC", "CANBK", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CUB", "CUMMINSIND", "DABUR", "DEEPAKNTR", "DIVISLAB", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAVELLS", "HCLTECH", "HDFC", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDPETRO", "HINDUNILVR", "IBULHSGFIN", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IGL", "INDHOTEL", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "L&TFH", "LALPATHLAB", "LICHSGFIN", "LT", "LTI", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "METROPOLIS", "MFSL", "MGL", "MINDTREE", "MOTHERSUMI", "MPHASIS", "MRF", "MUTHOOTFIN", "NAM-INDIA", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PFIZER", "PIDILITIND", "PIIND", "PNB", "POWERGRID", "PVR", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBILIFE", "SBIN", "SHREECEM", "SIEMENS", "SRF", "SRTRANSFIN", "SUNPHARMA", "SUNTV", "TATACHEM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ASTRAL", "STAR" };
        Dictionary<int, string[]> expiryDates = new Dictionary<int, string[]>();
        public NSEData()
        {
            LoadExpiryDates();
            InitializeComponent();
            DateFrom.Value = new DateTime(2021, 01, 01);
        }

        private void LoadExpiryDates()
        {
            // https://www1.nseindia.com/products/content/derivatives/equities/historical_fo.htm            -- Expiry Dates
            //https://www1.nseindia.com/products/content/equities/equities/eq_security.htm                  -- Delivery
            expiryDates.Add(1, new string[] { "28", "Jan" });
            expiryDates.Add(2, new string[] { "25", "Feb" });
            expiryDates.Add(3, new string[] { "25", "Mar" });
            expiryDates.Add(4, new string[] { "29", "Apr" });
            expiryDates.Add(5, new string[] { "27", "May" });
            expiryDates.Add(6, new string[] { "24", "Jun" });
            expiryDates.Add(7, new string[] { "29", "Jul" });
            expiryDates.Add(8, new string[] { "26", "Aug" });
            expiryDates.Add(9, new string[] { "30", "Sep" });
            expiryDates.Add(10, new string[] { "28", "Oct" });
            expiryDates.Add(11, new string[] { "30", "Nov" });
            expiryDates.Add(12, new string[] { "30", "Dec" });
        }
        private void DownloadData_Click(object sender, EventArgs e)
        {

            string scrip = string.Empty;//Convert.ToString(comboBox1.SelectedItem);
            //List<string> scripsToDownload = SharesList.Items;
            int selectedSharesCount = SharesList.SelectedItems.Count;
            if (selectedSharesCount != 0)
            {
                for (int i = 0; i <= selectedSharesCount - 1; i++)
                {
                    DateTime dateTimeFrom = DateFrom.Value;
                    DateTime dateTimeTo = DateTo.Value;
                    scrip = Convert.ToString(SharesList.SelectedItems[i]);
                    DateTime latestDataDateForScrip = GetLatestDataDateForScrip(scrip);

                    if (dateTimeFrom < latestDataDateForScrip)
                    {
                        dateTimeFrom = latestDataDateForScrip.Date.AddDays(1);
                    }
                    bool isDateTimeFromAWeekend = (dateTimeFrom.DayOfWeek == DayOfWeek.Saturday || dateTimeFrom.DayOfWeek == DayOfWeek.Sunday);
                    bool isDateTimeToAWeekend = (dateTimeTo.DayOfWeek == DayOfWeek.Saturday || dateTimeTo.DayOfWeek == DayOfWeek.Sunday);
                    int diffInDays = (dateTimeTo.Date - dateTimeFrom.Date).Days;

                    if (!(diffInDays < 2 && isDateTimeFromAWeekend && isDateTimeToAWeekend) || diffInDays > 2)
                    {
                        DownloadEquityData(dateTimeFrom.ToString("dd-MM-yyyy"), dateTimeTo.ToString("dd-MM-yyyy"), scrip);
                        int monthFrom = dateTimeFrom.Month;
                        int monthTo = dateTimeTo.Month;
                        if ((monthTo - monthFrom) == 0)
                        {
                            string expiryDate = string.Concat(expiryDates[monthFrom][0], "-", expiryDates[monthFrom][1], "-2021");
                            DownloadFuturesData(dateTimeFrom.ToString("dd-MM-yyyy"), dateTimeTo.ToString("dd-MM-yyyy"), expiryDate, scrip);
                        }
                        else
                        {
                            //bool isFirstIteration = true;
                            for (int month = monthFrom; month <= monthTo + 1; month++)
                            {
                                string dateFrom = string.Concat("01-", GetMonthIn2Digits(month), "-2021");
                                //string toDate = string.Concat(expiryDates[month][0], "-",GetMonthIn2Digits(month), "-2021");
                                string toDate = string.Concat(DateTime.DaysInMonth(2021, month), "-", GetMonthIn2Digits(month), "-2021");
                                string expiryDate = string.Concat(expiryDates[month][0], "-", expiryDates[month][1], "-2021");
                                DownloadFuturesData(dateFrom, toDate, expiryDate, scrip);
                                //toDate = string.Concat(expiryDates[month][0], "-", GetMonthIn2Digits(month), "-2021");
                                expiryDate = string.Concat(expiryDates[month + 1][0], "-", expiryDates[month + 1][1], "-2021");
                                DownloadFuturesData(dateFrom, toDate, expiryDate, scrip);
                            }
                        }
                    }
                    else
                    {
                        MessageBox.Show("Please select dates so that atleaset one day is not a weekend and data is not already in the system", "Select correct date range", MessageBoxButtons.OK);
                    }
                }
            }
            else
            {
                MessageBox.Show("Please select a Share to download", "Select a Share", MessageBoxButtons.OK);
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
            string downloadDerivate = "https://nseindia.com/api/historical/fo/derivatives?&from=" + startDate + "&to=" + endDate + "&expiryDate=" + expiryDate + "&instrumentType=FUTSTK&symbol=" + scrip + "&csv=true";
            Process oMyProcess = Process.Start(downloadDerivate);
        }
        private static void DownloadEquityData(string startDate, string endDate, string scrip)
        {
            //string fileLocation = "C:\\Work\\NSE\\Quote-Equity-" + scrip + "-EQ-" + startDate + "-to-" + endDate + ".csv";
            string dataDownload = "https://www.nseindia.com/api/historical/cm/equity?symbol=" + scrip + "&series=[%22EQ%22]&from=" + startDate + "&to=" + endDate + "&csv=false";

            //string derivativeFileLocation = "C:\\Work\\NSE\\Quote-FAO-" + scrip + "-" + startDate + "-to-" + endDate + ".csv";
            //string downloadDerivate = "https://nseindia.com/api/historical/fo/derivatives?&from=" + startDate + "&to=" + endDate + "&expiryDate=" + expiryDate + "&instrumentType=FUTSTK&symbol=" + scrip + "&csv=true";

            Process oMyProcess = Process.Start(dataDownload);
            //Process oMyProcess1 = Process.Start(downloadDerivate);

            //bool isFileDownloaded = false;
            //bool isDerivativeFileDownloaded = false;

            //if (!File.Exists(fileLocation))
            //{
            //    Process oMyProcess = Process.Start(dataDownload);
            //    while (!isFileDownloaded)
            //    {
            //        if (File.Exists(fileLocation))
            //        {
            //            Thread.Sleep(20000);
            //            isFileDownloaded = true;
            //        }
            //    }
            //    oMyProcess.CloseMainWindow();
            //    oMyProcess.Close();
            //}

            //if (!File.Exists(derivativeFileLocation))
            //{
            //    Process oMyProcess1 = Process.Start(downloadDerivate);
            //    while (!isDerivativeFileDownloaded)
            //    {
            //        if (File.Exists(fileLocation))
            //        {
            //            Thread.Sleep(20000);
            //            isDerivativeFileDownloaded = true;
            //        }
            //    }
            //    oMyProcess1.CloseMainWindow();
            //    oMyProcess1.Close();
            //}

            //GetData(derivativeFileLocation);
        }

        private static DataTable GetData(string filePath)
        {
            DataTable dtCsv = new DataTable();
            //string filePath = derivativeFileLocation;
            using (StreamReader sr = new StreamReader(filePath))
            {
                while (!sr.EndOfStream)
                {
                    string Fulltext = sr.ReadToEnd().ToString(); //read full file text  
                    string[] rows = Fulltext.Split('\n'); //split full file text into rows  
                    for (int i = 0; i < rows.Length; i++)
                    {
                        Regex CSVParser = new Regex(",(?=(?:[^\"]*\"[^\"]*\")*(?![^\"]*\"))");
                        string[] rowValues = CSVParser.Split(rows[i]); //split each row with comma to get individual values  
                        {
                            if (i == 0)
                            {
                                for (int j = 0; j < rowValues.Length; j++)
                                {
                                    string columnName = rowValues[j].Replace("\"", "").Replace(" ", "").Replace(".", "").Trim().ToUpper();
                                    if (columnName == "DATE" || columnName == "EXPIRYDATE")
                                    {
                                        dtCsv.Columns.Add(columnName); //add headers
                                        dtCsv.Columns[j].DataType = typeof(DateTime);
                                    }
                                    else if (columnName == "SERIES")
                                    {
                                        dtCsv.Columns.Add(columnName);
                                        dtCsv.Columns[j].DataType = typeof(string);
                                    }
                                    else
                                    {
                                        dtCsv.Columns.Add(columnName);
                                        dtCsv.Columns[j].DataType = typeof(double);
                                    }
                                }
                            }
                            else
                            {
                                DataRow dr = dtCsv.NewRow();
                                for (int k = 0; k < rowValues.Length; k++)
                                {
                                    if (dtCsv.Columns[k].ColumnName == "DATE" || dtCsv.Columns[k].ColumnName == "EXPIRYDATE")
                                    {
                                        dr[k] = DateTime.ParseExact(rowValues[k].Replace("\"", ""), "dd-MMM-yyyy", CultureInfo.InvariantCulture);
                                    }
                                    else if (dtCsv.Columns[k].ColumnName == "SERIES")
                                    {
                                        dr[k] = rowValues[k].Replace("\"", "");
                                    }
                                    else
                                    {
                                        double value = 0;
                                        double.TryParse(rowValues[k].Replace("\"", ""), out value);
                                        dr[k] = value;
                                    }
                                }
                                dtCsv.Rows.Add(dr); //add other rows  
                            }
                        }
                    }
                }
            }

            return dtCsv;
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

        //private void MoveDataToDatabase_Click(object sender, EventArgs e)
        //{

        //    string download = string.Empty;

        //    //for (int i = 0; i < 2; i++)
        //    //{
        //    //    if (i == 0)
        //    //    {
        //    //        //download = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY";
        //    //        download = "https://www.nseindia.com/api/option-chain-equities?symbol=TATAMOTORS";
        //    //    }
        //    //    else
        //    //    {
        //    //        download = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY";
        //    //    }
        //    using (WebClient wc = new WebClient())
        //    {
        //        download = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY";
        //        //wc.Headers.Add(HttpRequestHeader.Cookie, "bm_sv=8EEB9E8D3D0E2814795D833BBE82105C~chWDuZWZp9ne3+68X00V5I/UGMlo9Smqgoe6kCNZGdawd7Ueiryx4xXbdi/GSmzs3CPsZN0Jrgw+wN4Z7vZlY4iMN/keIkTpOxBm1snWZuwfGrBO4pBlKkgHJK/hyIBVOquzyMnnCcdtcXCz3oVWZV513sbJbsSlgUTuLHiwtnk=; Domain=.nseindia.com; Path=/; Max-Age=4231; HttpOnly");
        //        wc.Headers.Add(HttpRequestHeader.Cookie, "bm_sv=EA70C4E49DAC147BDF33B93C7EBD3B58~3l7RzZu8Lat2OtXYrYtfwgJMaA/1HlFLgxg9GwhBMGmIUDPiK8QYoP0GZIo1yMyLHvTAtjAhSOKm7IwkG7c6tJZGNVX2t4GOPjyPUTK5cCRLpLHMcCicdaf5tHZ++FLsSssAq1dunUGg2Zn8JuSnp7kOLFGexs+OW1L00V9xMUw=; Domain=.nseindia.com; Path=/; Max-Age=6; HttpOnly");
        //        var json = wc.DownloadString(download);


        //        //CookieContainer cookies = new CookieContainer();
        //        //HttpClientHandler handler = new HttpClientHandler();
        //        //handler.CookieContainer = cookies;

        //        //HttpClient client = new HttpClient(handler);
        //        //HttpResponseMessage response = client.GetAsync("https://www.nseindia.com/").Result;

        //        //Uri uri = new Uri("https://www.nseindia.com/");
        //        //IEnumerable<Cookie> responseCookies = cookies.GetCookies(uri).Cast<Cookie>();
        //        //foreach (Cookie cookie in responseCookies)
        //        //    Console.WriteLine(cookie.Name + ": " + cookie.Value);
        //    }

        //    using (WebClient wc1 = new WebClient())
        //    {
        //        download = "https://www.nseindia.com/api/option-chain-equities?symbol=TATAMOTORS";
        //        //wc.Headers.Add(HttpRequestHeader.Cookie, "bm_sv=8EEB9E8D3D0E2814795D833BBE82105C~chWDuZWZp9ne3+68X00V5I/UGMlo9Smqgoe6kCNZGdawd7Ueiryx4xXbdi/GSmzs3CPsZN0Jrgw+wN4Z7vZlY4iMN/keIkTpOxBm1snWZuwfGrBO4pBlKkgHJK/hyIBVOquzyMnnCcdtcXCz3oVWZV513sbJbsSlgUTuLHiwtnk=; Domain=.nseindia.com; Path=/; Max-Age=4231; HttpOnly");
        //        wc1.Headers.Add(HttpRequestHeader.Cookie, "bm_sv=EA70C4E49DAC147BDF33B93C7EBD3B58~3l7RzZu8Lat2OtXYrYtfwgJMaA/1HlFLgxg9GwhBMGmIUDPiK8QYoP0GZIo1yMyLHvTAtjAhSOKm7IwkG7c6tJZGNVX2t4GOPjyPUTK5cCRLpLHMcCicdaf5tHZ++FLsSssAq1dunUGg2Zn8JuSnp7kOLFGexs+OW1L00V9xMUw=; Domain=.nseindia.com; Path=/; Max-Age=6; HttpOnly");
        //        var json = wc1.DownloadString(download);


        //        //CookieContainer cookies = new CookieContainer();
        //        //HttpClientHandler handler = new HttpClientHandler();
        //        //handler.CookieContainer = cookies;

        //        //HttpClient client = new HttpClient(handler);
        //        //HttpResponseMessage response = client.GetAsync("https://www.nseindia.com/").Result;

        //        //Uri uri = new Uri("https://www.nseindia.com/");
        //        //IEnumerable<Cookie> responseCookies = cookies.GetCookies(uri).Cast<Cookie>();
        //        //foreach (Cookie cookie in responseCookies)
        //        //    Console.WriteLine(cookie.Name + ": " + cookie.Value);
        //    }
        //    //Thread.Sleep(20000);
        //    //}
        //}
        private void MoveDataToDatabase_Click(object sender, EventArgs e)
        {
            int selectedSharesCount = SharesList.SelectedItems.Count;
            if (selectedSharesCount != 0)
            {
                string scripName = string.Empty;
                string scripNameEquity = string.Empty;
                string scripNameDerivative = string.Empty;
                string fileName = string.Empty;

                for (int i = 0; i <= selectedSharesCount - 1; i++)
                {
                    scripName = Convert.ToString(SharesList.SelectedItems[i]);
                    scripNameEquity = string.Concat("Quote-Equity-", scripName, "*");
                    scripNameDerivative = string.Concat("Quote-FAO-", scripName, "*");
                    string nseFolder = @"C:\Work\NSE";
                    string[] filesEquity = Directory.GetFiles(nseFolder, scripNameEquity);
                    string[] filesDerivative = Directory.GetFiles(nseFolder, scripNameDerivative); //Getting Text files
                    string filter = string.Format("DATE >= #{0}# AND DATE <= #{1}#", DateFrom.Value.ToString("MM/dd/yyyy"), DateTo.Value.ToString("MM/dd/yyyy"));

                    for (int j = 0; j < filesEquity.Length; j++)
                    {
                        fileName = filesEquity[j];
                        DataTable oDataTale = GetData(filesEquity[j]);
                        // https://forums.asp.net/t/1701322.aspx?Convert+a+datatable+column+from+string+to+integer

                        if (oDataTale.Rows.Count > 0)
                        {
                            if (oDataTale.Select(filter).Count() > 0)
                            {
                                MoveEquityToDatabase(oDataTale.Select(filter).CopyToDataTable(), scripName, true);
                            }
                        }
                    }

                    for (int j = 0; j < filesDerivative.Length; j++)
                    {
                        fileName = filesDerivative[j];
                        DataTable oDataTale = GetData(filesDerivative[j]);
                        if (oDataTale.Rows.Count > 0)
                        {
                            if (oDataTale.Select(filter).Count() > 0)
                            {
                                MoveEquityToDatabase(oDataTale.Select(filter).CopyToDataTable(), scripName, false);
                            }
                        }
                    }
                    // Excel in the video: https://drive.google.com/file/d/1Blu3DRDd9Jia9mkcbpSZsM1d5oKlWkk9/view
                    //https://youtu.be/2fbRrJq7WHc?list=PLbLq81ZyYiocOcUD4XQ5FS7JOcfAL5MxF&t=2033
                }
                MessageBox.Show("Data moved to database successfully", "Data Updated Successfully", MessageBoxButtons.OK);
            }
            else
            {
                MessageBox.Show("Please select a Share to process", "Select a Share", MessageBoxButtons.OK);
            }
        }

        private static void MoveEquityToDatabase(DataTable equityData, string scripName, bool isEquityData)
        {
            //SqlConnection connection = new SqlConnection("Data Source=.\\SQLEXPRESS;Initial Catalog=SharesData;Integrated Security=True");
            using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
            {
                if (isEquityData)
                {
                    using (SqlCommand cmd = new SqlCommand("UpdateEquityData", con))
                    {
                        cmd.CommandType = CommandType.StoredProcedure;

                        cmd.Parameters.Add("@EquityData", SqlDbType.Structured).Value = equityData;
                        cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;
                        cmd.Parameters.Add("@IsEquityData", SqlDbType.Bit).Value = isEquityData;

                        con.Open();
                        cmd.ExecuteNonQuery();
                    }
                }
                else
                {
                    using (SqlCommand cmd = new SqlCommand("UpdateEquityData", con))
                    {
                        cmd.CommandType = CommandType.StoredProcedure;

                        cmd.Parameters.Add("@FutureData", SqlDbType.Structured).Value = equityData;
                        cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;
                        cmd.Parameters.Add("@IsEquityData", SqlDbType.Bit).Value = isEquityData;

                        con.Open();
                        cmd.ExecuteNonQuery();
                    }
                }
            }
        }

        private DateTime GetLatestDataDateForScrip(string scripName)
        {
            DateTime latestDataDate = new DateTime(2021, 01, 01);
            using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
            {
                using (SqlCommand cmd = new SqlCommand("GetLatestDataDateForScrip", con))
                {
                    cmd.CommandType = CommandType.StoredProcedure;
                    cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;

                    con.Open();
                    DataTable oDataTable = new DataTable();
                    oDataTable.Load(cmd.ExecuteReader());
                    if (oDataTable.Rows[0][0] != DBNull.Value)
                    {
                        latestDataDate = Convert.ToDateTime(oDataTable.Rows[0][0]);
                    }
                }
            }

            return latestDataDate;
        }

        private void ProcessData_Click(object sender, EventArgs e)
        {
            int selectedSharesCount = SharesList.SelectedItems.Count;
            if (selectedSharesCount != 0)
            {
                for (int i = 0; i <= selectedSharesCount - 1; i++)
                {
                    string scripName = Convert.ToString(SharesList.SelectedItems[i]);
                    using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
                    {
                        using (SqlCommand cmd = new SqlCommand("ProcessData", con))
                        {
                            cmd.CommandType = CommandType.StoredProcedure;

                            cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;

                            con.Open();
                            cmd.ExecuteNonQuery();
                        }
                    }
                }
                MessageBox.Show("Data processing is completed!!!", "Data processing completed", MessageBoxButtons.OK);
            }
            else
            {
                MessageBox.Show("Please select a scrip to process", "Scrip not selected", MessageBoxButtons.RetryCancel);
            }
        }

        private void ChartRepresentation_Click(object sender, EventArgs e)
        {
            try
            {
                chart1.Series.Clear();
                DataTable oDataTable = null;
                int selectedSharesCount = SharesList.SelectedItems.Count;
                int maxRange = 40000000;
                int minRange = -40000000;
                if (selectedSharesCount == 1)
                {
                    string scripName = Convert.ToString(SharesList.SelectedItems[0]);
                    using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
                    {
                        using (SqlCommand cmd = new SqlCommand("GetChartData", con))
                        {
                            cmd.CommandType = CommandType.StoredProcedure;
                            cmd.Parameters.Add("@FromDate", SqlDbType.VarChar).Value = DateFrom.Value;
                            cmd.Parameters.Add("@ToDate", SqlDbType.VarChar).Value = DateTo.Value;
                            cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;
                            cmd.Parameters.Add("@MaxRange", SqlDbType.Int);
                            cmd.Parameters["@MaxRange"].Direction = ParameterDirection.Output;
                            cmd.Parameters.Add("@MinRange", SqlDbType.Int);
                            cmd.Parameters["@MinRange"].Direction = ParameterDirection.Output;

                            con.Open();
                            oDataTable = new DataTable();
                            oDataTable.Load(cmd.ExecuteReader());

                            maxRange = (int)cmd.Parameters["@MaxRange"].Value;
                            minRange = (int)cmd.Parameters["@MinRange"].Value;
                        }
                    }

                    if (oDataTable != null)
                    {
                        DateTime[] x = (from p in oDataTable.AsEnumerable()
                                        orderby p.Field<DateTime>("DATE") ascending
                                        select p.Field<DateTime>("DATE")).ToArray();

                        int[] y = (from p in oDataTable.AsEnumerable()
                                   orderby p.Field<DateTime>("DATE") ascending
                                   select p.Field<int>("CUMMULATIVEOPENINTEREST")).ToArray();

                        int[] y1 = (from p in oDataTable.AsEnumerable()
                                    orderby p.Field<DateTime>("DATE") ascending
                                    select p.Field<int>("LONG")).ToArray();

                        int[] y2 = (from p in oDataTable.AsEnumerable()
                                    orderby p.Field<DateTime>("DATE") ascending
                                    select p.Field<int>("SHORT")).ToArray();

                        int[] y3 = (from p in oDataTable.AsEnumerable()
                                    orderby p.Field<DateTime>("DATE") ascending
                                    select p.Field<int>("LONGSTILLNOW")).ToArray();

                        int[] y4 = (from p in oDataTable.AsEnumerable()
                                    orderby p.Field<DateTime>("DATE") ascending
                                    select p.Field<int>("SHORTSTILLNOW")).ToArray();


                        Series s = new Series("CUMMULATIVEOPENINTEREST");
                        s.LegendText = "OI Stats";
                        s.ChartType = SeriesChartType.Line;
                        s.XValueType = ChartValueType.DateTime;

                        Series s1 = new Series("LONG");
                        s1.LegendText = "LONG";
                        s1.ChartType = SeriesChartType.Line;
                        s1.XValueType = ChartValueType.DateTime;

                        Series s2 = new Series("SHORT");
                        s2.LegendText = "SHORT";
                        s2.ChartType = SeriesChartType.Line;
                        s2.XValueType = ChartValueType.DateTime;

                        Series s3 = new Series("LongsTillNow");
                        s3.LegendText = "LongsTillNow";
                        s3.ChartType = SeriesChartType.Line;
                        s3.XValueType = ChartValueType.DateTime;

                        Series s4 = new Series("ShortsTillNow");
                        s4.LegendText = "ShortsTillNow";
                        s4.ChartType = SeriesChartType.Line;
                        s4.XValueType = ChartValueType.DateTime;

                        chart1.ChartAreas[0].AxisX.LabelStyle.Format = "yyyy-MM-dd";
                        chart1.ChartAreas[0].AxisX.Interval = 1;
                        chart1.ChartAreas[0].AxisX.IntervalType = DateTimeIntervalType.Weeks;
                        chart1.ChartAreas[0].AxisX.IntervalOffset = 1;

                        chart1.ChartAreas[0].AxisY.Maximum = (double)maxRange;
                        chart1.ChartAreas[0].AxisY.Minimum = (double)(minRange - 100000);

                        chart1.ChartAreas[0].CursorY.AutoScroll = true;

                        s.Points.DataBindXY(x, y);
                        chart1.Series.Add(s);

                        s1.Points.DataBindXY(x, y1);
                        chart1.Series.Add(s1);

                        s2.Points.DataBindXY(x, y2);
                        chart1.Series.Add(s2);

                        s3.Points.DataBindXY(x, y3);
                        chart1.Series.Add(s3);

                        s4.Points.DataBindXY(x, y4);
                        chart1.Series.Add(s4);
                    }

                    //MessageBox.Show("Chart is created successfully!!!", "Chart Created", MessageBoxButtons.OK);
                }
                else if (selectedSharesCount > 1)
                {
                    MessageBox.Show("Please select only one scrip for charting", "Alert", MessageBoxButtons.OK);
                }
                else
                {
                    MessageBox.Show("Please select any scrip to create chart", "Alert", MessageBoxButtons.OK);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.ToString(), "Alert", MessageBoxButtons.OK);
            }
        }
    }
}
