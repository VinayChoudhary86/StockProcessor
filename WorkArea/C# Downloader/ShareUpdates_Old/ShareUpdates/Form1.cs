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
using System.Net;
using System.Web;
using System.Net.Mime;

// When price declines but no change in OI that is an alarm
namespace ShareUpdates
{

    public partial class NSEData : Form
    {
        string[] indexNames = { "NIFTY", "BANKNIFTY" };
        string[] shares = { "DIXON", "TATAMOTORS", "TCS", "INFY", "RELIANCE", "INDUSINDBK", "RVNL" };
        Dictionary<int, string[]> expiryDates = new Dictionary<int, string[]>();
        string[] filesDownloaded = { };
        public NSEData()
        {
            LoadExpiryDates();
            InitializeComponent();
            DateFrom.Value = new DateTime(2021, 01, 01);
            DateTo.Value = new DateTime(2021, 06, 30);
        }

        private int MonthStringToNumber(string monthName)
        {
            return DateTime.ParseExact(monthName, "MMMM", CultureInfo.CurrentCulture).Month;
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
            //string scrip;
            DateTime dateTimeFrom = DateFrom.Value;
            DateTime dateTimeTo = DateTo.Value;
            if (string.IsNullOrEmpty(scrip))
            {
                scrip = Convert.ToString(SharesList.SelectedItems[i]);
            }

            string downloadDeliveryData = "https://www.nseindia.com/api/historicalOR/generateSecurityWiseHistoricalData?from=" + DateFrom.Value.ToString("dd-MM-yyyy") + "&to=" + DateTo.Value.ToString("dd-MM-yyyy") + "&symbol=" + scrip + "&type=priceVolumeDeliverable&series=EQ&csv=true";
            Process oMyProcess1 = Process.Start(downloadDeliveryData);

            bool isDataAvailable = false;
            TimeSpan start = new TimeSpan(21, 0, 0); //10 o'clock

            if (DateTime.Now.TimeOfDay > start)
            {
                isDataAvailable = true;
            }

            //Checks if data is available on NSE to downlaod
            if (dateTimeFrom.Date < DateTime.Now.Date || (dateTimeFrom.Date == DateTime.Now.Date && isDataAvailable))
            {
                bool isDateTimeFromAWeekend = (dateTimeFrom.DayOfWeek == DayOfWeek.Saturday || dateTimeFrom.DayOfWeek == DayOfWeek.Sunday);
                bool isDateTimeToAWeekend = (dateTimeTo.DayOfWeek == DayOfWeek.Saturday || dateTimeTo.DayOfWeek == DayOfWeek.Sunday);
                int diffInDays = (dateTimeTo.Date - dateTimeFrom.Date).Days;

                if (scrip != "NIFTY" && scrip != "BANKNIFTY")
                {
                    DownloadEquityData(dateTimeFrom.ToString("dd-MM-yyyy"), dateTimeTo.ToString("dd-MM-yyyy"), scrip);
                }
                int monthFrom = 0;
                int monthTo = 0;

                monthFrom = getMonthIndex(dateTimeFrom);
                monthTo = getMonthIndex(dateTimeTo);
                
                for (int month = monthFrom; month <= monthTo; month++)
                {
                    string dateFrom = string.Empty;
                    string toDate = string.Empty;
                    string expiryDate = string.Empty;
                    int year = Convert.ToInt32(expiryDates[month][2]);

                    dateFrom = string.Concat("01-", expiryDates[month][3], "-", year);
                    toDate = string.Concat(DateTime.DaysInMonth(year, Convert.ToInt32(expiryDates[month][3])), "-", GetMonthIn2Digits(Convert.ToInt32(expiryDates[month][3])), "-", year);

                    expiryDate = string.Concat(expiryDates[month][0], "-", expiryDates[month][1], "-", year);
                    DownloadFuturesData(dateFrom, toDate, expiryDate, scrip);

                    expiryDate = string.Concat(expiryDates[month + 1][0], "-", expiryDates[month + 1][1], "-", Convert.ToInt32(expiryDates[month+1][2]));
                    DownloadFuturesData(dateFrom, toDate, expiryDate, scrip);

                    //expiryDate = string.Concat(expiryDates[month + 2][0], "-", expiryDates[month + 2][1], Convert.ToInt32(expiryDates[month+2][2]));
                    //DownloadFuturesData(dateFrom, toDate, expiryDate, scrip);
                }

                isScripDataDownloaded = true;
            }

            //return scrip;
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
            //string fileLocation = "C:\\Work\\NSE\\Quote-Equity-" + scrip + "-EQ-" + startDate + "-to-" + endDate + ".csv";
            string dataDownload = "https://www.nseindia.com/api/historical/cm/equity?symbol=" + scrip + "&series=[%22EQ%22]&from=" + startDate + "&to=" + endDate + "&csv=false";

            Process oMyProcess = Process.Start(dataDownload);           
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
                                    if (string.IsNullOrEmpty(rowValues[k]))
                                    {
                                        break;
                                    }
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

        private void MoveDataToDatabase_Click(object sender, EventArgs e)
        {
            label3.Visible = true;
            progressBar1.Visible = true;
            string scripName = string.Empty;
            if (chkBankNifty.Checked)
            {
                scripName = "BANKNIFTY";
            }
            else if (chkNifty.Checked)
            {
                scripName = "NIFTY";
            }
            int selectedSharesCount = SharesList.SelectedItems.Count;
            if (selectedSharesCount != 0 || !string.IsNullOrEmpty(scripName))
            {

                string scripNameEquity = string.Empty;
                string scripNameDerivative = string.Empty;
                string fileName = string.Empty;

                if (string.IsNullOrEmpty(scripName))
                {
                    for (int i = 0; i <= selectedSharesCount - 1; i++)
                        MoveCSVDataToDatabase(ref scripName, out scripNameEquity, out scripNameDerivative, ref fileName, i);
                }
                else
                {
                    MoveCSVDataToDatabase(ref scripName, out scripNameEquity, out scripNameDerivative, ref fileName, 0);
                }
                MessageBox.Show("Data moved to database successfully", "Data Updated Successfully", MessageBoxButtons.OK);
            }
            else
            {
                MessageBox.Show("Please select a Share to process", "Select a Share", MessageBoxButtons.OK);
            }
        }

        private void MoveCSVDataToDatabase(ref string scripName, out string scripNameEquity, out string scripNameDerivative, ref string fileName, int i)
        {
            if (Array.IndexOf(indexNames, scripName) == -1)
                scripName = Convert.ToString(SharesList.SelectedItems[i]);
            scripNameEquity = string.Concat("Quote-Equity-", scripName, "*");
            scripNameDerivative = string.Concat("Quote-FAO-", scripName, "*");
            string nseFolder = @"C:\Work\Code\Code_Personal\Code_Personal\NSE\ShareUpdates\Files";
            string[] filesEquity = Directory.GetFiles(nseFolder, scripNameEquity);
            string[] filesDerivative = Directory.GetFiles(nseFolder, scripNameDerivative); //Getting Text files
            string filter = string.Format("DATE >= #{0}# AND DATE <= #{1}#", DateFrom.Value.ToString("MM/dd/yyyy"), DateTo.Value.ToString("MM/dd/yyyy"));

            if (scripName != "BANKNIFTY" && scripName != "NIFTY")
            {
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
            }
            else
            {
                string[] files = null;
                files = Directory.GetFiles(nseFolder, string.Concat(scripName, "*"));

                if (files != null && files.Length == 1)
                {
                    DataTable oDataTable = GetData(files[0]);
                    MoveEquityToDatabase(oDataTable.Select(filter).CopyToDataTable(), scripName, true, true);
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

        private static void MoveEquityToDatabase(DataTable equityData, string scripName, bool isEquityData, bool isIndexData = false)
        {
            //SqlConnection connection = new SqlConnection("Data Source=.\\SQLEXPRESS;Initial Catalog=SharesData;Integrated Security=True");
            using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
            {
                if (isIndexData)
                {
                    using (SqlCommand cmd = new SqlCommand("UpdateEquityData", con))
                    {
                        cmd.CommandType = CommandType.StoredProcedure;

                        cmd.Parameters.Add("@IndexData", SqlDbType.Structured).Value = equityData;
                        cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;
                        cmd.Parameters.Add("@IsEquityData", SqlDbType.Bit).Value = isEquityData;
                        cmd.Parameters.Add("@IsIndexData", SqlDbType.Bit).Value = isIndexData;

                        con.Open();
                        cmd.ExecuteNonQuery();
                    }
                }
                else if (isEquityData)
                {
                    using (SqlCommand cmd = new SqlCommand("UpdateEquityData", con))
                    {
                        cmd.CommandType = CommandType.StoredProcedure;

                        cmd.Parameters.Add("@EquityData", SqlDbType.Structured).Value = equityData;
                        cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;
                        cmd.Parameters.Add("@IsEquityData", SqlDbType.Bit).Value = isEquityData;
                        cmd.Parameters.Add("@IsIndexData", SqlDbType.Bit).Value = isIndexData;

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
                        cmd.Parameters.Add("@IsIndexData", SqlDbType.Bit).Value = isIndexData;

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

        private DateTime GetLatestEquityDeliveryDataDate(string tableName)
        {
            DateTime latestDataDate = new DateTime(2021, 01, 01);
            using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
            {
                using (SqlCommand cmd = new SqlCommand("GetLatestEquityDeliveryDataDate", con))
                {
                    cmd.CommandType = CommandType.StoredProcedure;
                    cmd.Parameters.Add("@TableName", SqlDbType.VarChar).Value = tableName;
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
            label3.Visible = true;
            progressBar1.Visible = true;
            progressBar1.Maximum = 100;
            progressBar1.Step = 1;
            progressBar1.Value = 1;

            string scripName = string.Empty;
            if (chkBankNifty.Checked)
            {
                scripName = "BANKNIFTY";
            }
            else if (chkNifty.Checked)
            {
                scripName = "NIFTY";
            }

            int selectedSharesCount = SharesList.SelectedItems.Count;
            if (selectedSharesCount != 0 || !string.IsNullOrEmpty(scripName))
            {
                if (string.IsNullOrEmpty(scripName))
                {
                    for (int i = 0; i <= selectedSharesCount - 1; i++)
                    {
                        scripName = Convert.ToString(SharesList.SelectedItems[i]);
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

                        progressBar1.Value = (i + 1) * 100 / selectedSharesCount;
                    }
                }
                else
                {
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
                    progressBar1.Value = 100;
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
                string scripName = string.Empty;
                if (chkBankNifty.Checked)
                {
                    scripName = "BANKNIFTY";
                }
                else if (chkNifty.Checked)
                {
                    scripName = "NIFTY";
                }

                chart1.Series.Clear();
                chart1.ChartAreas.Clear();
                DataTable oDataTable = null;
                int selectedSharesCount = SharesList.SelectedItems.Count;
                int maxRange = 40000000;
                int minRange = -40000000;

                int maxRangeDaily = 500000;
                int minRangeDaily = -500000;

                if (selectedSharesCount == 1 || !string.IsNullOrEmpty(scripName))
                {
                    if (string.IsNullOrEmpty(scripName))
                    {
                        scripName = Convert.ToString(SharesList.SelectedItems[0]);
                    }
                    using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
                    {
                        using (SqlCommand cmd = new SqlCommand("GetChartData", con))
                        {
                            cmd.CommandType = CommandType.StoredProcedure;
                            cmd.Parameters.Add("@FromDate", SqlDbType.VarChar).Value = DateFrom.Value;
                            cmd.Parameters.Add("@ToDate", SqlDbType.VarChar).Value = DateTo.Value;
                            cmd.Parameters.Add("@ScripName", SqlDbType.VarChar).Value = scripName;
                            cmd.Parameters.Add("@IsPercent", SqlDbType.Bit).Value = chkIsPercent.Checked;

                            cmd.Parameters.Add("@MaxRange", SqlDbType.Int);
                            cmd.Parameters["@MaxRange"].Direction = ParameterDirection.Output;
                            cmd.Parameters.Add("@MinRange", SqlDbType.Int);
                            cmd.Parameters["@MinRange"].Direction = ParameterDirection.Output;

                            //cmd.Parameters.Add("@MaxRangeDaily", SqlDbType.Int);
                            //cmd.Parameters["@MaxRangeDaily"].Direction = ParameterDirection.Output;
                            //cmd.Parameters.Add("@MinRangeDaily", SqlDbType.Int);
                            //cmd.Parameters["@MinRangeDaily"].Direction = ParameterDirection.Output;

                            con.Open();
                            oDataTable = new DataTable();
                            oDataTable.Load(cmd.ExecuteReader());

                            maxRange = (int)cmd.Parameters["@MaxRange"].Value;
                            minRange = (int)cmd.Parameters["@MinRange"].Value;

                            //maxRangeDaily = (int)cmd.Parameters["@MaxRangeDaily"].Value;
                            //minRangeDaily = (int)cmd.Parameters["@MinRangeDaily"].Value;
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

                        int[] y5 = (from p in oDataTable.AsEnumerable()
                                    orderby p.Field<DateTime>("DATE") ascending
                                    select 0).ToArray();

                        ChartArea chartArea0 = new ChartArea("Line");
                        chartArea0.AxisX.LabelStyle.Format = "yyyy-MM-dd";
                        chartArea0.AxisX.Interval = 5;
                        chartArea0.AxisX.IntervalType = DateTimeIntervalType.Days;
                        chartArea0.AxisX.IntervalOffset = 1;

                        chartArea0.AxisY.Maximum = chkIsPercent.Checked ? 100 : (double)maxRange;
                        chartArea0.AxisY.Minimum = chkIsPercent.Checked ? -100 : (double)(minRange - 100000);
                        chartArea0.CursorY.AutoScroll = true;

                        chart1.ChartAreas.Add(chartArea0);

                        Series s = new Series("CUMMULATIVEOPENINTEREST");
                        s.LegendText = "OI Stats";
                        s.Color = System.Drawing.Color.Blue;
                        s.ChartType = SeriesChartType.Line;
                        s.XValueType = ChartValueType.DateTime;
                        s.IsXValueIndexed = true;
                        s.Points.DataBindXY(x, y);
                        chart1.Series.Add(s);

                        Series s1 = new Series("LONG");
                        s1.LegendText = "LONG";
                        s1.Color = System.Drawing.Color.LightGreen;
                        s1.ChartType = SeriesChartType.Line;
                        s1.XValueType = ChartValueType.DateTime;
                        s1.IsXValueIndexed = true;
                        s1.Points.DataBindXY(x, y1);
                        chart1.Series.Add(s1);

                        Series s2 = new Series("SHORT");
                        s2.LegendText = "SHORT";
                        s2.Color = System.Drawing.Color.LightPink;
                        s2.ChartType = SeriesChartType.Line;
                        s2.XValueType = ChartValueType.DateTime;
                        s2.IsXValueIndexed = true;
                        s2.Points.DataBindXY(x, y2);
                        chart1.Series.Add(s2);

                        Series s3 = new Series("LongsTillNow");
                        s3.LegendText = "LongsTillNow";
                        s3.Color = System.Drawing.Color.Green;
                        s3.ChartType = SeriesChartType.Line;
                        s3.XValueType = ChartValueType.DateTime;
                        s3.IsXValueIndexed = true;
                        s3.Points.DataBindXY(x, y3);
                        chart1.Series.Add(s3);

                        Series s4 = new Series("ShortsTillNow");
                        s4.LegendText = "ShortsTillNow";
                        s4.Color = System.Drawing.Color.Red;
                        s4.ChartType = SeriesChartType.Line;
                        s4.XValueType = ChartValueType.DateTime;
                        s4.IsXValueIndexed = true;
                        s4.Points.DataBindXY(x, y4);
                        chart1.Series.Add(s4);

                        Series s5 = new Series("ZeroLine");
                        s5.LegendText = "ZeroLine";
                        s5.Color = System.Drawing.Color.Black;
                        s5.BorderWidth = 2;
                        s5.ChartType = SeriesChartType.Line;
                        s5.XValueType = ChartValueType.DateTime;
                        s5.IsXValueIndexed = true;
                        s5.Points.DataBindXY(x, y5);
                        chart1.Series.Add(s5);

                        s.ChartArea = "Line";
                        s3.ChartArea = "Line";
                        s4.ChartArea = "Line";
                        s5.ChartArea = "Line";
                        s1.ChartArea = "Line";
                        s2.ChartArea = "Line";

                        chart1.Height = 900;
                        chart1.Width = 1900;

                        chartArea0.AxisX.MajorGrid.LineWidth = 0;
                    }
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

        private void DownLoadOptionChain()
        {
            //https://www.nseindia.com/api/historical/fo/derivatives?&from=19-07-2021&to=19-08-2021&optionType=CE&strikePrice=36000.00&expiryDate=02-Sep-2021&instrumentType=OPTIDX&symbol=BANKNIFTY&csv=true
            //https://www.nseindia.com/api/historical/fo/derivatives?&from=19-08-2020&to=19-08-2021&optionType=CE&strikePrice=300.00&expiryDate=30-Sep-2021&instrumentType=OPTSTK&symbol=TATAMOTORS&csv
            OldWay();
        }

        private static void OldWay()
        {
            //string download = string.Empty;

            ////for (int i = 0; i < 2; i++)
            ////{
            ////    if (i == 0)
            ////    {
            ////        //download = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY";
            ////        download = "https://www.nseindia.com/api/option-chain-equities?symbol=TATAMOTORS";
            ////    }
            ////    else
            ////    {
            ////        download = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY";
            ////    }

            //using (WebClient wc = new WebClient())
            //{
            //    //download = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY";
            //    //wc.Headers.Add(HttpRequestHeader.Cookie, "bm_sv=EA70C4E49DAC147BDF33B93C7EBD3B58~3l7RzZu8Lat2OtXYrYtfwgJMaA/1HlFLgxg9GwhBMGmIUDPiK8QYoP0GZIo1yMyLHvTAtjAhSOKm7IwkG7c6tJZGNVX2t4GOPjyPUTK5cCRLpLHMcCicdaf5tHZ++FLsSssAq1dunUGg2Zn8JuSnp7kOLFGexs+OW1L00V9xMUw=; Domain=.nseindia.com; Path=/; Max-Age=6; HttpOnly");
            //    //var json = wc.DownloadString(download);
            //    //wc.Dispose();
            //}

            //using (WebClient wc1 = new WebClient())
            //{
            //    download = "https://www.nseindia.com/api/option-chain-equities?symbol=TATASTEEL";
            //    //download = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY";
            //    //wc1.Headers.Add(HttpRequestHeader.Cookie, "_ga=GA1.2.1118795063.1614845166; nsit=zWtZzXCvmGYMHMgMZ3_I2F_I; nseappid=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkubnNlIiwiYXVkIjoiYXBpLm5zZSIsImlhdCI6MTYyOTEyOTMxOCwiZXhwIjoxNjI5MTMyOTE4fQ.wU7bEW8Ww3a4UDZqdr-Rl63aEE2STvV2dct_phuslAE; bm_mi=FC600737417691748C360C7ECB7D49F1~3DJlIUTr5zvPG0WYbh03FJl4xma+xntgsDEKswlpcaHOGY6HRAITLWxH4adifvvSBiTY77QPvCFe+bINpzrGktbf9aQZwuilPc7AIdx7Yn44ZQsdEDibaTDLjYm6O1EoAfhKgkiSSrsv5yTXSjjf8h0p2Bn7Uo5VQN+5JXElE4dgJZ5ZFL28fTAuhSy3j1j6DnbjuyoN7m3LsmFCvoGQr53Img8pcSutubLVS4wJjMxTR0IsHJlquDqHDEBSDO/gnlA2czBj7VqVJ0RxDuYYpw==; _gid=GA1.2.1922372528.1629129321; _gat_UA-143761337-1=1; ak_bmsc=9B86E7A699CA662F251B60692CED03BF~000000000000000000000000000000~YAAQjbYRYODhF7J6AQAA9LGsTwxzm8yFsg+QcUpZDgtviGCGMsb/LZuVlieHFSI57xVT16o0VKEY4lIJhCVavh0AvFmtzrMO/9KBM9NwJXN8pFoTRElbrlDJbZVdF2plH4G5T02UT9ULmAvI+ovObuy9otBV4EcYdNI5Ry6yWnswSK44C7NOWtOpcs/mXd/iuA0cWzOl/PrjI+sSy4yER6wUz0Gv6lDI8e88GW/GjUZdW4Y4yjOQvc4J9Ghm86h1Fg0BhnMO2uuE3TlOjJVNVBE5tTQ2KTv8Gh51fC6IOhGmHcNzJlo+6Am0F30VRFhJeazwweI5ZuqLLoVpXEabiTbFo715z8YtLT5W1Ne/1AYCBH3xHlaJPgRfbvBhYaJ/IjBJwROZnkVCTT3G3GxoX6uz8bl/DvcYpzcyAV8=; bm_sv=2311317E0F4F0CAB41E1A331094AC75C~w8Xqffrf4mqJwMaDF5/6xhgF8cwwFN/oBMsx4twWDaEp/wcxSWJ+zZKqOv4lfpWYB1MmOcCIHcBYpoRFrZ0tW0rigGTS1DMSpMyYVpzbCNK/ToD9SRcoquX8JXZWMc8A9AJwyVLCB4EJd8v3mzSimNAIOH6S7HEuvMbeDI9W4nQ=; RT=\"z = 1 & dm = nseindia.com & si = 103dd154 - 7f9e-4640 - 8d3f - 9b7f6121582a & ss = ksetj8k7 & sl = 0 & tt = 0 & bcn =% 2F % 2F685d5b1b.akstat.io % 2F & r = fd32ae0d544088d42dcac548e979762e & ul = 3ul & hd = 3yf\"");
            //    //wc1.Headers.Add(HttpRequestHeader.ContentType, "application/json");
            //    wc1.Headers.Add(HttpRequestHeader.Cookie, "_ga=GA1.2.1118795063.1614845166; nsit=zWtZzXCvmGYMHMgMZ3_I2F_I; nseappid=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkubnNlIiwiYXVkIjoiYXBpLm5zZSIsImlhdCI6MTYyOTEyOTMxOCwiZXhwIjoxNjI5MTMyOTE4fQ.wU7bEW8Ww3a4UDZqdr-Rl63aEE2STvV2dct_phuslAE; bm_mi=FC600737417691748C360C7ECB7D49F1~3DJlIUTr5zvPG0WYbh03FJl4xma+xntgsDEKswlpcaHOGY6HRAITLWxH4adifvvSBiTY77QPvCFe+bINpzrGktbf9aQZwuilPc7AIdx7Yn44ZQsdEDibaTDLjYm6O1EoAfhKgkiSSrsv5yTXSjjf8h0p2Bn7Uo5VQN+5JXElE4dgJZ5ZFL28fTAuhSy3j1j6DnbjuyoN7m3LsmFCvoGQr53Img8pcSutubLVS4wJjMxTR0IsHJlquDqHDEBSDO/gnlA2czBj7VqVJ0RxDuYYpw==; _gid=GA1.2.1922372528.1629129321; ak_bmsc=9B86E7A699CA662F251B60692CED03BF~000000000000000000000000000000~YAAQjbYRYODhF7J6AQAA9LGsTwxzm8yFsg+QcUpZDgtviGCGMsb/LZuVlieHFSI57xVT16o0VKEY4lIJhCVavh0AvFmtzrMO/9KBM9NwJXN8pFoTRElbrlDJbZVdF2plH4G5T02UT9ULmAvI+ovObuy9otBV4EcYdNI5Ry6yWnswSK44C7NOWtOpcs/mXd/iuA0cWzOl/PrjI+sSy4yER6wUz0Gv6lDI8e88GW/GjUZdW4Y4yjOQvc4J9Ghm86h1Fg0BhnMO2uuE3TlOjJVNVBE5tTQ2KTv8Gh51fC6IOhGmHcNzJlo+6Am0F30VRFhJeazwweI5ZuqLLoVpXEabiTbFo715z8YtLT5W1Ne/1AYCBH3xHlaJPgRfbvBhYaJ/IjBJwROZnkVCTT3G3GxoX6uz8bl/DvcYpzcyAV8=; RT=\"z = 1 & dm = nseindia.com & si = 103dd154 - 7f9e-4640 - 8d3f - 9b7f6121582a & ss = ksetj8k7 & sl = 0 & tt = 0 & bcn =% 2F % 2F685d5b1b.akstat.io % 2F & r = fd32ae0d544088d42dcac548e979762e & ul = 3ul & hd = 3yf\"; bm_sv=2311317E0F4F0CAB41E1A331094AC75C~w8Xqffrf4mqJwMaDF5/6xhgF8cwwFN/oBMsx4twWDaEp/wcxSWJ+zZKqOv4lfpWYB1MmOcCIHcBYpoRFrZ0tW0rigGTS1DMSpMyYVpzbCNLJwYgf6imGKauQcrEfB+VbBUD+C19TOMeQimjaOie/KhlCyrBe2pGvbYNEJBsI2eU=");
            //    wc1.Headers.Add(HttpRequestHeader.UserAgent, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36");
            //    //wc1.Headers.Add(HttpRequestHeader.Accept, "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9");
            //    wc1.Headers.Add(HttpRequestHeader.Accept, "application/json");
            //    wc1.Headers.Add(HttpRequestHeader.AcceptEncoding, "gzip, deflate, br");
            //    wc1.Headers.Add(HttpRequestHeader.AcceptLanguage, "pl,en-US;q=0.9,en;q=0.8,fr;q=0.7");

            //    var json = wc1.DownloadString(download);


            //    //    //CookieContainer cookies = new CookieContainer();
            //    //    //HttpClientHandler handler = new HttpClientHandler();
            //    //    //handler.CookieContainer = cookies;

            //    //    //HttpClient client = new HttpClient(handler);
            //    //    //HttpResponseMessage response = client.GetAsync("https://www.nseindia.com/").Result;

            //    //    //Uri uri = new Uri("https://www.nseindia.com/");
            //    //    //IEnumerable<Cookie> responseCookies = cookies.GetCookies(uri).Cast<Cookie>();
            //    //    //foreach (Cookie cookie in responseCookies)
            //    //    //    Console.WriteLine(cookie.Name + ": " + cookie.Value);
            //    //}
            //    //Thread.Sleep(20000);
            //}
        }

        private void DownloadDelivery_Click(object sender, EventArgs e)
        {
            //https://www1.nseindia.com/archives/equities/mto/MTO
            //// https://www1.nseindia.com//content/historical/EQUITIES/2022/FEB/cm14FEB2022bhav.csv.zip

            // Download delivery data
            DateTime latestProcessedDeliveryDate = GetLatestEquityDeliveryDataDate("DELIVERY");
            DateTime dateTimeFrom = DateFrom.Value;
            if (dateTimeFrom < latestProcessedDeliveryDate)
            {
                dateTimeFrom = latestProcessedDeliveryDate;
            }

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
            latestProcessedDeliveryDate = GetLatestEquityDeliveryDataDate("BHAVCOPY");
            dateTimeFrom = DateFrom.Value;
            if (dateTimeFrom < latestProcessedDeliveryDate)
            {
                dateTimeFrom = latestProcessedDeliveryDate;
            }

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
        private static DataTable GetDeliveryData(string filePath, DateTime date)
        {
            DataTable dtCsv = new DataTable();
            //string filePath = derivativeFileLocation;
            if (File.Exists(filePath))
            {
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
                                if (i == 3)
                                {
                                    int columnCount = 0;
                                    for (int j = 0; j < rowValues.Length; j++)
                                    {
                                        string columnName = rowValues[j].Replace("\"", "").Replace(" ", "").Replace(".", "").Trim().ToUpper();
                                        if (columnName == "NAMEOFSECURITY")
                                        {
                                            dtCsv.Columns.Add("SCRIPNAME"); //add headers
                                            dtCsv.Columns[columnCount].DataType = typeof(string);
                                            columnCount++;
                                        }
                                        else if (columnName == "QUANTITYTRADED")
                                        {
                                            dtCsv.Columns.Add("TYPE");
                                            dtCsv.Columns[columnCount].DataType = typeof(string);
                                            columnCount++;
                                        }
                                        else if (columnName == "DELIVERABLEQUANTITY(GROSSACROSSCLIENTLEVEL)")
                                        {
                                            dtCsv.Columns.Add("QUANTITYTRADED");
                                            dtCsv.Columns[columnCount].DataType = typeof(float);
                                            columnCount++;
                                        }
                                        else if (columnName == "%OFDELIVERABLEQUANTITYTOTRADEDQUANTITY")
                                        {
                                            dtCsv.Columns.Add("DELIVERABLEQUANTITY");
                                            dtCsv.Columns[columnCount].DataType = typeof(float);
                                            columnCount++;
                                        }
                                    }
                                    dtCsv.Columns.Add("DATE");
                                    dtCsv.Columns[columnCount].DataType = typeof(DateTime);
                                }
                                else if (i > 3)
                                {
                                    DataRow dr = dtCsv.NewRow();
                                    for (int k = 0; k < dtCsv.Columns.Count; k++)
                                    {
                                        if (string.IsNullOrEmpty(rowValues[k]))
                                        {
                                            break;
                                        }
                                        if (dtCsv.Columns[k].ColumnName == "SCRIPNAME" || dtCsv.Columns[k].ColumnName == "TYPE")
                                        {
                                            dr[k] = Convert.ToString(rowValues[k + 2]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "QUANTITYTRADED" || dtCsv.Columns[k].ColumnName == "DELIVERABLEQUANTITY")
                                        {
                                            dr[k] = Convert.ToDouble(rowValues[k + 2]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "DATE")
                                        {
                                            dr[k] = date;
                                        }
                                    }
                                    dtCsv.Rows.Add(dr); //add other rows  
                                }
                            }
                        }
                    }
                }
            }

            return dtCsv;
        }
        private static DataTable GetBhavCopyData(string filePath, DateTime date)
        {
            DataTable dtCsv = new DataTable();
            if (File.Exists(filePath))
            {
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
                                    int columnCount = 0;
                                    for (int j = 0; j < rowValues.Length; j++)
                                    {
                                        string columnName = rowValues[j].Replace("\"", "").Replace(" ", "").Replace(".", "").Trim().ToUpper();
                                        if (columnName == "SYMBOL")
                                        {
                                            dtCsv.Columns.Add("SCRIPNAME"); //add headers
                                            dtCsv.Columns[columnCount].DataType = typeof(string);
                                            columnCount++;
                                        }
                                        else if (columnName == "SERIES")
                                        {
                                            dtCsv.Columns.Add("TYPE");
                                            dtCsv.Columns[columnCount].DataType = typeof(string);
                                            columnCount++;
                                        }
                                        else if (columnName == "OPEN" || columnName == "HIGH" || columnName == "LOW" || columnName == "CLOSE" || columnName == "LAST" || columnName == "PREVCLOSE")
                                        {
                                            dtCsv.Columns.Add(columnName);
                                            dtCsv.Columns[columnCount].DataType = typeof(float);
                                            columnCount++;
                                        }
                                        else if (columnName == "TOTTRDQTY")
                                        {
                                            dtCsv.Columns.Add("TOTALTRADEDQUANTITY");
                                            dtCsv.Columns[columnCount].DataType = typeof(float);
                                            columnCount++;
                                        }
                                        else if (columnName == "TOTTRDVAL")
                                        {
                                            dtCsv.Columns.Add("TOTALTRADEDVALUE");
                                            dtCsv.Columns[columnCount].DataType = typeof(float);
                                            columnCount++;
                                        }
                                        else if (columnName == "TOTALTRADES")
                                        {
                                            dtCsv.Columns.Add("TOTALTRADES");
                                            dtCsv.Columns[columnCount].DataType = typeof(float);
                                            columnCount++;
                                        }
                                        else if (columnName == "ISIN")
                                        {
                                            dtCsv.Columns.Add(columnName);
                                            dtCsv.Columns[columnCount].DataType = typeof(string);
                                            columnCount++;
                                        }
                                        else if (columnName == "TIMESTAMP")
                                        {
                                            dtCsv.Columns.Add("DATE");
                                            dtCsv.Columns[columnCount].DataType = typeof(DateTime);
                                            columnCount++;
                                        }
                                    }
                                }
                                else if (i > 0)
                                {
                                    DataRow dr = dtCsv.NewRow();
                                    for (int k = 0; k < dtCsv.Columns.Count; k++)
                                    {
                                        if (string.IsNullOrEmpty(rowValues[k]))
                                        {
                                            break;
                                        }
                                        if (dtCsv.Columns[k].ColumnName == "SCRIPNAME")
                                        {
                                            dr[k] = Convert.ToString(rowValues[k]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "TYPE")
                                        {
                                            dr[k] = Convert.ToString(rowValues[k]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "OPEN" || dtCsv.Columns[k].ColumnName == "HIGH" || dtCsv.Columns[k].ColumnName == "LOW" || dtCsv.Columns[k].ColumnName == "CLOSE" || dtCsv.Columns[k].ColumnName == "LAST" || dtCsv.Columns[k].ColumnName == "PREVCLOSE")
                                        {
                                            dr[k] = Convert.ToDouble(rowValues[k]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "TOTALTRADEDQUANTITY")
                                        {
                                            dr[k] = Convert.ToDouble(rowValues[k]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "TOTALTRADEDVALUE")
                                        {
                                            dr[k] = Convert.ToDouble(rowValues[k]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "TOTALTRADES")
                                        {
                                            dr[k] = Convert.ToDouble(rowValues[k]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "ISIN")
                                        {
                                            dr[k] = Convert.ToString(rowValues[k]);
                                        }
                                        else if (dtCsv.Columns[k].ColumnName == "DATE")
                                        {
                                            dr[k] = Convert.ToDateTime(rowValues[k]);
                                        }
                                    }
                                    dtCsv.Rows.Add(dr); //add other rows  
                                }
                            }
                        }
                    }
                }
            }

            return dtCsv;
        }
        private void MoveDeliveryDataToDatabase_Click(object sender, EventArgs e)
        {
            MoveDataToFilesFolder();
            DateTime latestDeliveryDataDate = GetLatestEquityDeliveryDataDate("DELIVERY");
            DateTime dateTimeFrom = DateFrom.Value;
            if (dateTimeFrom < latestDeliveryDataDate)
            {
                dateTimeFrom = latestDeliveryDataDate;
            }
            DateTime dateTimeTo = DateTo.Value;
            DateTime dateToDownload = dateTimeFrom;
            int days = (dateTimeTo - dateTimeFrom).Days + 1;
            for (int i = 1; i <= days; i++)
            {

                string year = dateToDownload.Year.ToString();
                string month = dateToDownload.ToString("MMM").ToUpper();
                string date = GetMonthIn2Digits(dateToDownload.Day);
                string fileName = string.Concat("DELIVERYDATA_", date, month, year, ".csv");
                string filePath = @"C:\Work\Code\Code_Personal\Code_Personal\NSE\ShareUpdates\Files\DeliveryData\" + fileName;
                DataTable equityDelivery = GetDeliveryData(filePath, dateToDownload);
                if (equityDelivery.Rows.Count > 0)
                {
                    equityDelivery = equityDelivery.Rows.Cast<DataRow>().Where(row => !row.ItemArray.All(field => field is DBNull || string.IsNullOrWhiteSpace(field as string))).CopyToDataTable();
                    InsertEquityDeliveryDataIntoDatabase(equityDelivery);
                }
                dateToDownload = dateToDownload.AddDays(1);
            }

            latestDeliveryDataDate = GetLatestEquityDeliveryDataDate("BHAVCOPY");
            dateTimeFrom = DateFrom.Value;
            if (dateTimeFrom < latestDeliveryDataDate)
            {
                dateTimeFrom = latestDeliveryDataDate;
            }
            dateTimeTo = DateTo.Value;
            dateToDownload = dateTimeFrom;
            days = (dateTimeTo - dateTimeFrom).Days + 1;
            for (int i = 1; i <= days; i++)
            {

                string year = dateToDownload.Year.ToString();
                string month = dateToDownload.ToString("MMM").ToUpper();
                string date = GetMonthIn2Digits(dateToDownload.Day);
                string fileName = string.Concat("cm", date, month, year, "bhav",".csv");
                string filePath = @"C:\Work\Code\Code_Personal\Code_Personal\NSE\ShareUpdates\Files\BhavCopy\" + fileName;
                DataTable bhavData = GetBhavCopyData(filePath, dateToDownload);
                if (bhavData.Rows.Count > 0)
                {
                    bhavData = bhavData.Rows.Cast<DataRow>().Where(row => !row.ItemArray.All(field => field is DBNull || string.IsNullOrWhiteSpace(field as string))).CopyToDataTable();
                    InsertEquityBhavCopyDataIntoDatabase(bhavData);
                }
                dateToDownload = dateToDownload.AddDays(1);
            }

            MessageBox.Show("Data moved to database successfully", "Data Updated Successfully", MessageBoxButtons.OK);
        }

        private void MoveDataToFilesFolder()
        {
            string bhavCopySouce = @"C:\Work\Code\Code_Personal\Code_Personal\NSE\ShareUpdates\ShareUpdates\bin\Debug";
            DateTime latestProcessedDeliveryDate = GetLatestEquityDeliveryDataDate("BHAVCOPY");
            DateTime dateTimeFrom = DateFrom.Value;
            if (dateTimeFrom < latestProcessedDeliveryDate)
            {
                dateTimeFrom = latestProcessedDeliveryDate;
            }

            DateTime dateTimeTo = DateTo.Value;
            DateTime dateToDownload = dateTimeFrom;
            int days = (dateTimeTo - dateTimeFrom).Days + 1;

            for (int i = 1; i <= days; i++)
            {
                string year = dateToDownload.Year.ToString();
                string month = dateToDownload.ToString("MMM").ToUpper();
                string date = GetMonthIn2Digits(dateToDownload.Day);
                string fileName = string.Concat("bhavcopy_", date, month, year, ".zip");
                string zipPath = string.Concat(bhavCopySouce, "\\", fileName);
                string extractPath = @"C:\Work\Code\Code_Personal\Code_Personal\NSE\ShareUpdates\Files\BhavCopy";
                string destFileName = string.Concat("cm", date, month, year, "bhav.csv");
                if (File.Exists(zipPath))
                {
                    if (new FileInfo(zipPath).Length > 0)
                    {
                        if (!File.Exists(string.Concat(extractPath, "\\", destFileName)))
                        {
                            System.IO.Compression.ZipFile.ExtractToDirectory(zipPath, extractPath);
                        }
                    }
                    File.Delete(zipPath);
                }
                dateToDownload = dateToDownload.AddDays(1);
            }

            string deliveryDataSouce = @"C:\Work\Code\Code_Personal\Code_Personal\NSE\ShareUpdates\ShareUpdates\bin\Debug";
            latestProcessedDeliveryDate = GetLatestEquityDeliveryDataDate("DELIVERY");
            dateTimeFrom = DateFrom.Value;
            if (dateTimeFrom < latestProcessedDeliveryDate)
            {
                dateTimeFrom = latestProcessedDeliveryDate;
            }

            dateTimeTo = DateTo.Value;
            dateToDownload = dateTimeFrom;
            days = (dateTimeTo - dateTimeFrom).Days + 1;

            for (int i = 1; i <= days; i++)
            {
                string year = dateToDownload.Year.ToString();
                string month = GetMonthIn2Digits(dateToDownload.Month);
                string date = GetMonthIn2Digits(dateToDownload.Day);
                string monthDestination = dateToDownload.ToString("MMM").ToUpper();
                string fileName = string.Concat("DELIVERYDATA_", date, month, year, ".csv");
                string fileNameDestination = string.Concat("DELIVERYDATA_", date, monthDestination, year, ".csv");
                string filePath = string.Concat(deliveryDataSouce, "\\", fileName);
                string extractPath = @"C:\Work\Code\Code_Personal\Code_Personal\NSE\ShareUpdates\Files\DeliveryData";
                string extractFilePath = string.Concat(extractPath, "\\", fileNameDestination);
                if (File.Exists(filePath))
                {
                    System.IO.File.Copy(filePath, extractFilePath, true);
                    File.Delete(filePath);
                }
                dateToDownload = dateToDownload.AddDays(1);
            }
        }

        private void InsertEquityDeliveryDataIntoDatabase(DataTable equityDelivery)
        {
            using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
            {

                using (SqlCommand cmd = new SqlCommand("UpdateEquityDeliveryData", con))
                {
                    cmd.CommandType = CommandType.StoredProcedure;
                    cmd.Parameters.Add("@EquityDeliveryData", SqlDbType.Structured).Value = equityDelivery;
                    con.Open();
                    cmd.ExecuteNonQuery();
                }
            }
        }
        private void InsertEquityBhavCopyDataIntoDatabase(DataTable bhavCopyData)
        {
            using (SqlConnection con = new SqlConnection("Data Source=.;Initial Catalog=SharesData;Integrated Security=True"))
            {

                using (SqlCommand cmd = new SqlCommand("UpdateBhavCopyData", con))
                {
                    cmd.CommandType = CommandType.StoredProcedure;
                    cmd.Parameters.Add("@BhavCopyData", SqlDbType.Structured).Value = bhavCopyData;
                    con.Open();
                    cmd.ExecuteNonQuery();
                }
            }

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

        private void DateFrom_ValueChanged(object sender, EventArgs e)
        {

        }
    }
}
