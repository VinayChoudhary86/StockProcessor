USE [SharesData]
GO

/****** Object:  Table [dbo].[Dates]    Script Date: 1/19/2022 2:53:27 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Dates](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[DATE] [datetime] NOT NULL
) ON [PRIMARY]

GO


USE [SharesData]
GO

/****** Object:  Table [dbo].[Equity]    Script Date: 1/19/2022 2:53:34 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

SET ANSI_PADDING ON
GO

CREATE TABLE [dbo].[Equity](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[SCRIPNAME] [varchar](200) NOT NULL,
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
	[NOOFTRADES] [numeric](30, 2) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO

SET ANSI_PADDING OFF
GO

USE [SharesData]
GO

/****** Object:  Table [dbo].[ExpiryDate]    Script Date: 1/19/2022 2:53:48 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[ExpiryDate](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[EXPIRYDATE] [datetime] NULL
) ON [PRIMARY]

GO

USE [SharesData]
GO

/****** Object:  Table [dbo].[FutureData]    Script Date: 1/19/2022 2:54:02 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

SET ANSI_PADDING ON
GO

CREATE TABLE [dbo].[FutureData](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[SCRIPNAME] [varchar](200) NOT NULL,
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
	[CHANGEINOI] [numeric](30, 2) NULL,
PRIMARY KEY CLUSTERED 
(
	[ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO

SET ANSI_PADDING OFF
GO

USE [SharesData]
GO

/****** Object:  Table [dbo].[ProcessedData]    Script Date: 1/19/2022 2:54:17 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

SET ANSI_PADDING ON
GO

CREATE TABLE [dbo].[ProcessedData](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[SCRIPNAME] [varchar](200) NOT NULL,
	[DATE] [datetime] NOT NULL,
	[PRICE] [numeric](30, 2) NULL,
	[DELIVERY] [numeric](30, 2) NULL,
	[CUMMULATIVEOPENINTEREST] [numeric](30, 2) NULL,
	[OPENINTERESTABSOLUTECHANGE] [numeric](30, 2) NULL,
	[PERCHANGE-PRICE] [numeric](30, 2) NULL,
	[PERCHAGE-DELIVERY] [numeric](30, 2) NULL,
	[PERCHANGE-CUMOPENINTEREST] [numeric](30, 2) NULL,
	[LONG] [numeric](30, 2) NULL,
	[SHORT] [numeric](30, 2) NULL,
	[VWAP] [numeric](30, 2) NULL,
	[HIGH] [numeric](30, 2) NULL,
	[LOW] [numeric](30, 2) NULL,
	[LONGSTILLNOW] [numeric](30, 2) NULL,
	[SHORTSTILLNOW] [numeric](30, 2) NULL
) ON [PRIMARY]

GO

SET ANSI_PADDING OFF
GO