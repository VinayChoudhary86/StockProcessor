namespace ShareUpdates
{
    partial class NSEData
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.components = new System.ComponentModel.Container();
            System.Windows.Forms.DataVisualization.Charting.ChartArea chartArea1 = new System.Windows.Forms.DataVisualization.Charting.ChartArea();
            System.Windows.Forms.DataVisualization.Charting.Legend legend1 = new System.Windows.Forms.DataVisualization.Charting.Legend();
            System.Windows.Forms.DataVisualization.Charting.Series series1 = new System.Windows.Forms.DataVisualization.Charting.Series();
            this.DownloadData = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.label2 = new System.Windows.Forms.Label();
            this.DateFrom = new System.Windows.Forms.DateTimePicker();
            this.DateTo = new System.Windows.Forms.DateTimePicker();
            this.SharesList = new System.Windows.Forms.ListBox();
            this.MoveDataToDatabase = new System.Windows.Forms.Button();
            this.DownloadAll = new System.Windows.Forms.CheckBox();
            this.ProcessData = new System.Windows.Forms.Button();
            this.chart1 = new System.Windows.Forms.DataVisualization.Charting.Chart();
            this.ChartRepresentation = new System.Windows.Forms.Button();
            this.imageList1 = new System.Windows.Forms.ImageList(this.components);
            this.progressBar1 = new System.Windows.Forms.ProgressBar();
            this.label3 = new System.Windows.Forms.Label();
            this.chkNifty = new System.Windows.Forms.CheckBox();
            this.chkBankNifty = new System.Windows.Forms.CheckBox();
            this.chkIsPercent = new System.Windows.Forms.CheckBox();
            this.DownloadDelivery = new System.Windows.Forms.Button();
            this.MoveDeliveryDataToDatabase = new System.Windows.Forms.Button();
            ((System.ComponentModel.ISupportInitialize)(this.chart1)).BeginInit();
            this.SuspendLayout();
            // 
            // DownloadData
            // 
            this.DownloadData.Location = new System.Drawing.Point(50, 67);
            this.DownloadData.Name = "DownloadData";
            this.DownloadData.Size = new System.Drawing.Size(113, 23);
            this.DownloadData.TabIndex = 0;
            this.DownloadData.Text = "Download Data";
            this.DownloadData.UseVisualStyleBackColor = true;
            this.DownloadData.Click += new System.EventHandler(this.DownloadData_Click);
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Location = new System.Drawing.Point(47, 9);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(56, 13);
            this.label1.TabIndex = 2;
            this.label1.Text = "From Date";
            // 
            // label2
            // 
            this.label2.AutoSize = true;
            this.label2.Location = new System.Drawing.Point(47, 35);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(46, 13);
            this.label2.TabIndex = 3;
            this.label2.Text = "To Date";
            // 
            // DateFrom
            // 
            this.DateFrom.Location = new System.Drawing.Point(145, 9);
            this.DateFrom.Name = "DateFrom";
            this.DateFrom.Size = new System.Drawing.Size(200, 20);
            this.DateFrom.TabIndex = 4;
            //this.DateFrom.ValueChanged += new System.EventHandler(this.DateFrom_ValueChanged);
            // 
            // DateTo
            // 
            this.DateTo.Location = new System.Drawing.Point(145, 35);
            this.DateTo.Name = "DateTo";
            this.DateTo.Size = new System.Drawing.Size(200, 20);
            this.DateTo.TabIndex = 5;
            // 
            // SharesList
            // 
            this.SharesList.FormattingEnabled = true;
            this.SharesList.Location = new System.Drawing.Point(506, 8);
            this.SharesList.Name = "SharesList";
            this.SharesList.SelectionMode = System.Windows.Forms.SelectionMode.MultiSimple;
            this.SharesList.Size = new System.Drawing.Size(180, 82);
            this.SharesList.TabIndex = 7;
            // 
            // MoveDataToDatabase
            // 
            this.MoveDataToDatabase.Location = new System.Drawing.Point(1027, 6);
            this.MoveDataToDatabase.Name = "MoveDataToDatabase";
            this.MoveDataToDatabase.Size = new System.Drawing.Size(173, 23);
            this.MoveDataToDatabase.TabIndex = 8;
            this.MoveDataToDatabase.Text = "Move Data To Database";
            this.MoveDataToDatabase.UseVisualStyleBackColor = true;
            //this.MoveDataToDatabase.Click += new System.EventHandler(this.MoveDataToDatabase_Click);
            // 
            // DownloadAll
            // 
            this.DownloadAll.AutoSize = true;
            this.DownloadAll.Location = new System.Drawing.Point(412, 8);
            this.DownloadAll.Name = "DownloadAll";
            this.DownloadAll.Size = new System.Drawing.Size(88, 17);
            this.DownloadAll.TabIndex = 9;
            this.DownloadAll.Text = "Download All";
            this.DownloadAll.UseVisualStyleBackColor = true;
            this.DownloadAll.CheckedChanged += new System.EventHandler(this.DownloadAll_CheckedChanged);
            // 
            // ProcessData
            // 
            this.ProcessData.Location = new System.Drawing.Point(1027, 37);
            this.ProcessData.Name = "ProcessData";
            this.ProcessData.Size = new System.Drawing.Size(173, 23);
            this.ProcessData.TabIndex = 10;
            this.ProcessData.Text = "Process Data";
            this.ProcessData.UseVisualStyleBackColor = true;
            //this.ProcessData.Click += new System.EventHandler(this.ProcessData_Click);
            // 
            // chart1
            // 
            chartArea1.Name = "ChartArea1";
            this.chart1.ChartAreas.Add(chartArea1);
            legend1.Name = "Legend1";
            this.chart1.Legends.Add(legend1);
            this.chart1.Location = new System.Drawing.Point(12, 96);
            this.chart1.Name = "chart1";
            series1.ChartArea = "ChartArea1";
            series1.Legend = "Legend1";
            series1.Name = "Series1";
            this.chart1.Series.Add(series1);
            this.chart1.Size = new System.Drawing.Size(1799, 698);
            this.chart1.TabIndex = 11;
            this.chart1.Text = "chart1";
            // 
            // ChartRepresentation
            // 
            this.ChartRepresentation.Location = new System.Drawing.Point(1206, 9);
            this.ChartRepresentation.Name = "ChartRepresentation";
            this.ChartRepresentation.Size = new System.Drawing.Size(276, 48);
            this.ChartRepresentation.TabIndex = 12;
            this.ChartRepresentation.Text = "Chart Representation";
            this.ChartRepresentation.UseVisualStyleBackColor = true;
            //this.ChartRepresentation.Click += new System.EventHandler(this.ChartRepresentation_Click);
            // 
            // imageList1
            // 
            this.imageList1.ColorDepth = System.Windows.Forms.ColorDepth.Depth8Bit;
            this.imageList1.ImageSize = new System.Drawing.Size(16, 16);
            this.imageList1.TransparentColor = System.Drawing.Color.Transparent;
            // 
            // progressBar1
            // 
            this.progressBar1.Location = new System.Drawing.Point(194, 101);
            this.progressBar1.Name = "progressBar1";
            this.progressBar1.Size = new System.Drawing.Size(1415, 23);
            this.progressBar1.TabIndex = 13;
            this.progressBar1.Visible = false;
            // 
            // label3
            // 
            this.label3.AutoSize = true;
            this.label3.Location = new System.Drawing.Point(47, 101);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(129, 13);
            this.label3.TabIndex = 14;
            this.label3.Text = "Data Processing Progress";
            this.label3.Visible = false;
            // 
            // chkNifty
            // 
            this.chkNifty.AutoSize = true;
            this.chkNifty.Location = new System.Drawing.Point(748, 8);
            this.chkNifty.Name = "chkNifty";
            this.chkNifty.Size = new System.Drawing.Size(47, 17);
            this.chkNifty.TabIndex = 15;
            this.chkNifty.Text = "Nifty";
            this.chkNifty.UseVisualStyleBackColor = true;
            // 
            // chkBankNifty
            // 
            this.chkBankNifty.AutoSize = true;
            this.chkBankNifty.Location = new System.Drawing.Point(748, 43);
            this.chkBankNifty.Name = "chkBankNifty";
            this.chkBankNifty.Size = new System.Drawing.Size(72, 17);
            this.chkBankNifty.TabIndex = 16;
            this.chkBankNifty.Text = "BankNifty";
            this.chkBankNifty.UseVisualStyleBackColor = true;
            // 
            // chkIsPercent
            // 
            this.chkIsPercent.AutoSize = true;
            this.chkIsPercent.Location = new System.Drawing.Point(909, 4);
            this.chkIsPercent.Name = "chkIsPercent";
            this.chkIsPercent.Size = new System.Drawing.Size(71, 17);
            this.chkIsPercent.TabIndex = 17;
            this.chkIsPercent.Text = "IsPercent";
            this.chkIsPercent.UseVisualStyleBackColor = true;
            // 
            // DownloadDelivery
            // 
            this.DownloadDelivery.Location = new System.Drawing.Point(1570, 12);
            this.DownloadDelivery.Name = "DownloadDelivery";
            this.DownloadDelivery.Size = new System.Drawing.Size(170, 23);
            this.DownloadDelivery.TabIndex = 18;
            this.DownloadDelivery.Text = "DownloadDelivery";
            this.DownloadDelivery.UseVisualStyleBackColor = true;
            this.DownloadDelivery.Click += new System.EventHandler(this.DownloadDelivery_Click);
            // 
            // MoveDeliveryDataToDatabase
            // 
            this.MoveDeliveryDataToDatabase.Location = new System.Drawing.Point(1570, 53);
            this.MoveDeliveryDataToDatabase.Name = "MoveDeliveryDataToDatabase";
            this.MoveDeliveryDataToDatabase.Size = new System.Drawing.Size(170, 23);
            this.MoveDeliveryDataToDatabase.TabIndex = 19;
            this.MoveDeliveryDataToDatabase.Text = "MoveDeliveryDataToDatabase";
            this.MoveDeliveryDataToDatabase.UseVisualStyleBackColor = true;
            //this.MoveDeliveryDataToDatabase.Click += new System.EventHandler(this.MoveDeliveryDataToDatabase_Click);
            // 
            // NSEData
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(1782, 795);
            this.Controls.Add(this.MoveDeliveryDataToDatabase);
            this.Controls.Add(this.DownloadDelivery);
            this.Controls.Add(this.chkIsPercent);
            this.Controls.Add(this.chkBankNifty);
            this.Controls.Add(this.chkNifty);
            this.Controls.Add(this.label3);
            this.Controls.Add(this.progressBar1);
            this.Controls.Add(this.ChartRepresentation);
            this.Controls.Add(this.chart1);
            this.Controls.Add(this.ProcessData);
            this.Controls.Add(this.DownloadAll);
            this.Controls.Add(this.MoveDataToDatabase);
            this.Controls.Add(this.SharesList);
            this.Controls.Add(this.DateTo);
            this.Controls.Add(this.DateFrom);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.DownloadData);
            this.Name = "NSEData";
            this.Text = "NSEData";
            this.Load += new System.EventHandler(this.NSEData_Load);
            ((System.ComponentModel.ISupportInitialize)(this.chart1)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Button DownloadData;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.DateTimePicker DateFrom;
        private System.Windows.Forms.DateTimePicker DateTo;
        private System.Windows.Forms.ListBox SharesList;
        private System.Windows.Forms.Button MoveDataToDatabase;
        private System.Windows.Forms.CheckBox DownloadAll;
        private System.Windows.Forms.Button ProcessData;
        private System.Windows.Forms.DataVisualization.Charting.Chart chart1;
        private System.Windows.Forms.Button ChartRepresentation;
        private System.Windows.Forms.ImageList imageList1;
        private System.Windows.Forms.ProgressBar progressBar1;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.CheckBox chkNifty;
        private System.Windows.Forms.CheckBox chkBankNifty;
        private System.Windows.Forms.CheckBox chkIsPercent;
        private System.Windows.Forms.Button DownloadDelivery;
        private System.Windows.Forms.Button MoveDeliveryDataToDatabase;
    }
}

