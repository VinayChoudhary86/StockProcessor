USE [SharesData]
GO

/****** Object:  UserDefinedTableType [dbo].[EquityData]    Script Date: 1/19/2022 2:56:17 PM ******/
CREATE TYPE [dbo].[EquityData] AS TABLE(
	[DATE] [datetime] NOT NULL,
	[SERIES] [varchar](100) NOT NULL,
	[OPEN] [numeric](30, 2) NOT NULL,
	[HIGH] [numeric](30, 2) NOT NULL,
	[LOW] [numeric](30, 2) NOT NULL,
	[PREVCLOSE] [numeric](30, 2) NOT NULL,
	[LTP] [numeric](30, 2) NOT NULL,
	[CLOSE] [numeric](30, 2) NOT NULL,
	[VWAP] [numeric](30, 2) NOT NULL,
	[52WH] [numeric](30, 2) NOT NULL,
	[52WL] [numeric](30, 2) NOT NULL,
	[VOLUME] [numeric](30, 2) NOT NULL,
	[VALUE] [numeric](30, 2) NOT NULL,
	[NOOFTRADES] [numeric](30, 2) NOT NULL
)
GO


USE [SharesData]
GO

/****** Object:  UserDefinedTableType [dbo].[FutureData]    Script Date: 1/19/2022 2:56:23 PM ******/
CREATE TYPE [dbo].[FutureData] AS TABLE(
	[DATE] [datetime] NOT NULL,
	[EXPIRYDATE] [datetime] NOT NULL,
	[OPTIONTYPE] [varchar](200) NOT NULL,
	[STRIKEPRICE] [int] NOT NULL,
	[OPENPRICE] [numeric](30, 2) NULL,
	[HIGHPRICE] [numeric](30, 2) NULL,
	[LOWPRICE] [numeric](30, 2) NULL,
	[CLOSEPRICE] [numeric](30, 2) NULL,
	[LASTPRICE] [numeric](30, 2) NULL,
	[SETTLEPRICE] [numeric](30, 2) NULL,
	[VOLUME] [numeric](30, 2) NULL,
	[VALUE] [numeric](30, 2) NULL,
	[PREMIUMVALUE] [numeric](30, 2) NULL,
	[OPENINTEREST] [numeric](30, 2) NULL,
	[CHANGEINOI] [numeric](30, 2) NULL
)
GO


USE [SharesData]
GO

/****** Object:  UserDefinedTableType [dbo].[IndexData]    Script Date: 1/19/2022 2:56:32 PM ******/
CREATE TYPE [dbo].[IndexData] AS TABLE(
	[DATE] [datetime] NOT NULL,
	[OPEN] [numeric](30, 2) NOT NULL,
	[HIGH] [numeric](30, 2) NOT NULL,
	[LOW] [numeric](30, 2) NOT NULL,
	[CLOSE] [numeric](30, 2) NOT NULL,
	[SHARESTRADED] [numeric](30, 2) NOT NULL,
	[TURNOVER(RSCR)] [numeric](30, 2) NOT NULL
)
GO


