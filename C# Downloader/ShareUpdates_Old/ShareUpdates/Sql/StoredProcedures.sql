USE [SharesData]
GO

/****** Object:  StoredProcedure [dbo].[GetChartData]    Script Date: 1/19/2022 2:54:42 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[GetChartData]
@FromDate DATETIME,
@ToDate DATETIME,
@ScripName NVARCHAR(200),
@IsPercent BIT,
@MaxRange INT OUT,
@MinRange INT OUT
AS
BEGIN
	
	DECLARE @Cummulative INT = ISNULL(( SELECT CUMMULATIVEOPENINTEREST FROM ProcessedData WHERE [DATE] = @FromDate AND SCRIPNAME = @ScripName ), 0)
	DECLARE @LongsTillNow INT = ISNULL(( SELECT LONGSTILLNOW FROM ProcessedData WHERE [DATE] = @FromDate AND SCRIPNAME = @ScripName ), 0)
	DECLARE @ShortsTillNow INT = ISNULL(( SELECT SHORTSTILLNOW FROM ProcessedData WHERE [DATE] = @FromDate AND SCRIPNAME = @ScripName ), 0)
	DECLARE @Longs INT = ISNULL(( SELECT LONG FROM ProcessedData WHERE [DATE] = @FromDate AND SCRIPNAME = @ScripName ), 0)
	DECLARE @Shorts INT = ISNULL(( SELECT SHORT FROM ProcessedData WHERE [DATE] = @FromDate AND SCRIPNAME = @ScripName ), 0)

	--DECLARE @iteration INT = 0
	DECLARE @Date DATE = @FromDate
	WHILE (@Cummulative = 0)
	BEGIN

		SET @Date = DATEADD(day, 1, @Date)
		SET @Cummulative = ISNULL(( SELECT CUMMULATIVEOPENINTEREST FROM ProcessedData WHERE [DATE] = @Date AND SCRIPNAME = @ScripName ), 0)
		SET @LongsTillNow = ISNULL(( SELECT LONGSTILLNOW FROM ProcessedData WHERE [DATE] = @Date AND SCRIPNAME = @ScripName ), 0)
		SET @ShortsTillNow = ISNULL(( SELECT SHORTSTILLNOW FROM ProcessedData WHERE [DATE] = @Date AND SCRIPNAME = @ScripName ), 0)
		SET @Longs = ISNULL(( SELECT LONG FROM ProcessedData WHERE [DATE] = @Date AND SCRIPNAME = @ScripName ), 0)
		SET @Shorts = ISNULL(( SELECT SHORT FROM ProcessedData WHERE [DATE] = @Date AND SCRIPNAME = @ScripName ), 0)
		--SET @iteration = @iteration + 1
		
	END

	--SELECT @Cummulative

	--DECLARE @MaxCummulative INT = ( SELECT CAST((SELECT MAX(CUMMULATIVEOPENINTEREST) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
	--	AND SCRIPNAME = @ScripName) AS INT) - @Cummulative )
	--DECLARE @MaxLongsTillNow INT = ( SELECT CAST((SELECT MAX(LONGSTILLNOW) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
	--	AND SCRIPNAME = @ScripName) AS INT) - @LongsTillNow )
	--DECLARE @MaxShortsTillNow INT = ( SELECT CAST((SELECT MAX(SHORTSTILLNOW) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
	--	AND SCRIPNAME = @ScripName) AS INT) - @ShortsTillNow )
	--DECLARE @MaxLong INT = ( SELECT CAST((SELECT MAX(LONG) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
	--	AND SCRIPNAME = @ScripName) AS INT) - @ShortsTillNow )

	DECLARE @MaxCummulative INT = CAST((SELECT MAX(CUMMULATIVEOPENINTEREST) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT)
	DECLARE @MaxLongsTillNow INT = CAST((SELECT MAX(LONGSTILLNOW) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT)
	DECLARE @MaxShortsTillNow INT = CAST((SELECT MAX(SHORTSTILLNOW) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT)
	DECLARE @MaxLong INT = CAST((SELECT MAX(LONG) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT)
	DECLARE @MaxShort INT = ( SELECT CAST((SELECT MAX(SHORT) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT) - @ShortsTillNow )

	DECLARE @MinCummulative INT = ( CAST((SELECT MIN(CUMMULATIVEOPENINTEREST) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT) )
	DECLARE @MinLongsTillNow INT = ( CAST((SELECT MIN(LONGSTILLNOW) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT) )
	DECLARE @MinShortsTillNow INT = ( CAST((SELECT MIN(SHORTSTILLNOW) FROM ProcessedData WHERE DATE >= @FromDate AND DATE <= @ToDate
		AND SCRIPNAME = @ScripName) AS INT) )
	



	DECLARE @MAX TABLE (VAL INT)

	INSERT INTO @MAX
	SELECT @MaxCummulative - @Cummulative
	
	INSERT INTO @MAX
	SELECT @MaxLongsTillNow - @LongsTillNow

	INSERT INTO @MAX
	SELECT @MaxShortsTillNow - @ShortsTillNow
	
	SET @MaxRange = ( SELECT MAX(VAL) FROM @MAX )



	DECLARE @MIN TABLE (VAL INT)

	INSERT INTO @MIN
	SELECT @MinCummulative - @Cummulative
	
	INSERT INTO @MIN
	SELECT @MinLongsTillNow - @LongsTillNow

	INSERT INTO @MIN
	SELECT @MinShortsTillNow - @ShortsTillNow
	
	SET @MinRange = ( SELECT MIN(VAL) FROM @MIN )

	DECLARE @CUMMPER INT = ( 
		CASE WHEN @MinCummulative < 0 THEN 
			CASE WHEN -@MinCummulative >= @MaxCummulative THEN -@MinCummulative ELSE @MaxCummulative END 
		ELSE 
			CASE WHEN @MinCummulative >= @MaxCummulative THEN @MinCummulative ELSE @MaxCummulative END  
		END
	)

	DECLARE @LONGPER INT = ( 
		CASE WHEN @MinLongsTillNow < 0 THEN 
			CASE WHEN -@MinLongsTillNow >= @MaxLongsTillNow THEN -@MinLongsTillNow ELSE @MaxLongsTillNow END 
		ELSE 
			CASE WHEN @MinLongsTillNow >= @MaxLongsTillNow THEN @MinLongsTillNow ELSE @MaxLongsTillNow END  
		END
	)

	DECLARE @SHORTGPER INT = ( 
		CASE WHEN @MinShortsTillNow < 0 THEN 
			CASE WHEN -@MinShortsTillNow >= @MaxShortsTillNow THEN -@MinShortsTillNow ELSE @MaxShortsTillNow END 
		ELSE 
			CASE WHEN @MinShortsTillNow >= @MaxShortsTillNow THEN @MinShortsTillNow ELSE @MaxShortsTillNow END  
		END
	)

	IF (@IsPercent = 1)
	BEGIN
		
		SELECT DATE, CAST(ISNULL(CUMMULATIVEOPENINTEREST, 0) * 100 / @CUMMPER AS INT) as 'CUMMULATIVEOPENINTEREST', 
		CAST(ISNULL(LONG, 0) * 100 / @MaxLong AS INT) as 'LONG', 
		CAST(ISNULL(SHORT, 0) * 100 / @MaxShort AS INT) as 'SHORT', 
		CAST(ISNULL(LONGSTILLNOW, 0) * 100 / @LONGPER AS INT) as 'LONGSTILLNOW', 
		CAST(ISNULL(SHORTSTILLNOW, 0) * 100 / @SHORTGPER AS INT) as 'SHORTSTILLNOW'
		FROM ProcessedData
		WHERE DATE >= @FromDate AND DATE <= @ToDate
			AND SCRIPNAME = @ScripName AND DATE IS NOT NULL
		ORDER BY DATE ASC
	END
	ELSE
	BEGIN

		SELECT DATE, ( ISNULL(CAST(CUMMULATIVEOPENINTEREST AS INT) - @Cummulative, 0) ) as 'CUMMULATIVEOPENINTEREST', 
		ISNULL(CAST(LONG AS INT), 0) as 'LONG', ISNULL(CAST(SHORT AS INT), 0) as 'SHORT',
		( ISNULL(CAST(LONGSTILLNOW AS INT) - @LongsTillNow, 0) ) AS 'LONGSTILLNOW', 
		( ISNULL(CAST(SHORTSTILLNOW AS INT) - @ShortsTillNow, 0)) AS 'SHORTSTILLNOW' 
		FROM ProcessedData
		WHERE DATE >= @FromDate AND DATE <= @ToDate
			AND SCRIPNAME = @ScripName AND DATE IS NOT NULL
		ORDER BY DATE ASC
	END
END
GO

USE [SharesData]
GO

/****** Object:  StoredProcedure [dbo].[GetLatestDataDateForScrip]    Script Date: 1/19/2022 2:55:00 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROCEDURE [dbo].[GetLatestDataDateForScrip]
@ScripName NVARCHAR(200)
AS
BEGIN
	
	SELECT MAX(DATE) FROM FutureData
	WHERE SCRIPNAME = @ScripName
END

GO


USE [SharesData]
GO

/****** Object:  StoredProcedure [dbo].[ProcessData]    Script Date: 1/19/2022 2:55:20 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE PROCEDURE [dbo].[ProcessData]
@ScripName NVARCHAR(200)
AS
BEGIN
	
	INSERT INTO Dates 
	(
		[DATE]
	)
	SELECT DISTINCT fd.DATE FROM FutureData fd
		LEFT JOIN Dates d ON fd.DATE = d.DATE
	WHERE d.ID IS NULL
	ORDER BY fd.DATE ASC

	--INSERT INTO [dbo].[ProcessedData]
 --   (
	--	[SCRIPNAME] ,[DATE] ,[PRICE] ,[DELIVERY] ,[CUMMULATIVEOPENINTEREST] ,[OPENINTERESTABSOLUTECHANGE] ,[PERCHANGE-PRICE]
 --          ,[PERCHAGE-DELIVERY] ,[PERCHANGE-CUMOPENINTEREST] ,[LONG] ,[SHORT] ,[VWAP] ,[HIGH] ,[LOW]
	--)
	INSERT INTO [dbo].[ProcessedData]
    (
		[DATE], [SCRIPNAME]
	)
	SELECT dt.[DATE], @ScripName
	FROM [Dates] dt
		LEFT JOIN [ProcessedData] pd ON dt.[DATE] = pd.[DATE] AND pd.[SCRIPNAME] = @ScripName
	WHERE pd.[DATE] IS NULL 
	ORDER BY [DATE] ASC

	--UPDATE pd
	--SET pd.CUMMULATIVEOPENINTEREST = SUM(fd.OPENINTEREST)
	--FROM [ProcessedData] pd
	--	JOIN FutureData fd ON pd.[DATE] = fd.[DATE] AND pd.[SCRIPNAME] = fd.[SCRIPNAME]
	--WHERE fd.SCRIPNAME = @ScripName
	--GROUP BY fd.[DATE]

	UPDATE pd
	SET pd.CUMMULATIVEOPENINTEREST = fd.CUMMULATIVEOPENINTEREST
	FROM [ProcessedData] pd
		JOIN (
			SELECT [SCRIPNAME], [DATE], SUM(OPENINTEREST) AS 'CUMMULATIVEOPENINTEREST'
			FROM [FutureData] 
			GROUP BY [SCRIPNAME], [DATE]
		) as fd ON pd.DATE = fd.DATE AND pd.SCRIPNAME = fd.SCRIPNAME
	WHERE pd.SCRIPNAME = @ScripName

	--IF(@ScripName <> 'NIFTY' AND @ScripName <> 'BANKNIFTY')
	--BEGIN
		UPDATE pd
		SET pd.PRICE	=  e.[CLOSE],
			pd.HIGH		= e.HIGH,
			pd.LOW		= e.LOW,
			pd.VWAP		= e.VWAP
		FROM [ProcessedData] pd 
			JOIN Equity e ON pd.DATE = e.DATE AND e.SCRIPNAME = pd.SCRIPNAME
		WHERE pd.SCRIPNAME = @ScripName
	--END
	--ELSE
	--BEGIN
	--	UPDATE pd
	--	SET pd.PRICE	=  f.CLOSEPRICE,
	--		pd.HIGH		= f.HIGHPRICE,
	--		pd.LOW		= f.LOWPRICE,
	--		pd.VWAP		= NULL
	--	FROM [ProcessedData] pd 
	--		JOIN FutureData f ON pd.DATE = f.DATE AND f.SCRIPNAME = pd.SCRIPNAME
	--	WHERE pd.SCRIPNAME = @ScripName
	--END

	DECLARE @DATA TABLE 
	(
		ID INT IDENTITY(1,1), 
		DATAID INT, 
		SCRIPNAME NVARCHAR(200), 
		DATE DATETIME, 
		PRICE NUMERIC (30,2),
		DELIVERY NUMERIC (30,2),
		CUMMULATIVEOPENINTEREST NUMERIC(30,2),
		OPENINTERESTABSOLUTECHANGE NUMERIC (30,2),
		[PERCENTAGE-PRICE] NUMERIC (30,2),
		[PERCENTAGE-DELIVERY] NUMERIC (30,2),
		[PERCENTAGE-CUMOPENINTEREST] NUMERIC (30,2),
		LONG NUMERIC (30,2),
		SHORT NUMERIC (30,2),
		VWAP NUMERIC (30,2),
		HIGH NUMERIC (30,2),
		LOW NUMERIC (30,2)
	)

	INSERT INTO @DATA
	(
		DATAID, SCRIPNAME, DATE, PRICE, DELIVERY, CUMMULATIVEOPENINTEREST, OPENINTERESTABSOLUTECHANGE, 
		[PERCENTAGE-PRICE], [PERCENTAGE-DELIVERY], [PERCENTAGE-CUMOPENINTEREST], LONG,
		SHORT, VWAP, HIGH, LOW
	)
	SELECT ID, SCRIPNAME, DATE, PRICE, DELIVERY, CUMMULATIVEOPENINTEREST, OPENINTERESTABSOLUTECHANGE, 
		[PERCHANGE-PRICE], [PERCHAGE-DELIVERY], [PERCHANGE-CUMOPENINTEREST], LONG,
		SHORT, VWAP, HIGH, LOW
	FROM [ProcessedData]
	WHERE SCRIPNAME = @ScripName
	ORDER BY DATE ASC

	DECLARE @iteration INT = 1
	DECLARE @TotalCount INT = ( SELECT COUNT(1) FROM @DATA )

	WHILE (@iteration <= @TotalCount)
	BEGIN

		IF(@iteration <> 1)
		BEGIN
			
			DECLARE @previousPrice NUMERIC(30,2) = ( SELECT PRICE FROM @DATA WHERE ID = (@iteration - 1) )
			DECLARE @currentPrice NUMERIC(30,2) = ( SELECT PRICE FROM @DATA WHERE ID = (@iteration) )

			DECLARE @previousOI NUMERIC(30,2) = ( SELECT CUMMULATIVEOPENINTEREST FROM @DATA WHERE ID = (@iteration - 1) )
			DECLARE @currentOI NUMERIC(30,2) = ( SELECT CUMMULATIVEOPENINTEREST FROM @DATA WHERE ID = (@iteration) )

			UPDATE pd
			SET pd.[PERCHANGE-PRICE] = ((@currentPrice - @previousPrice) / @previousPrice) * 100,
				pd.OPENINTERESTABSOLUTECHANGE = @currentOI - @previousOI,
				pd.[PERCHANGE-CUMOPENINTEREST] = ((@currentOI - @previousOI) / @previousOI) *100
			FROM [ProcessedData] pd
				JOIN @DATA d ON pd.ID = d.DATAID
			WHERE d.ID = @iteration
		END
		SET @iteration = @iteration + 1
	END
	
	UPDATE ProcessedData
	SET LONG  = CASE WHEN ( ([PERCHANGE-PRICE] > 0 AND [PERCHANGE-CUMOPENINTEREST] > 0) OR ([PERCHANGE-PRICE] < 0 AND [PERCHANGE-CUMOPENINTEREST] < 0) ) THEN [OPENINTERESTABSOLUTECHANGE] ELSE 0 END, 
		SHORT = CASE WHEN ( ([PERCHANGE-PRICE] > 0 AND [PERCHANGE-CUMOPENINTEREST] < 0) OR ([PERCHANGE-PRICE] < 0 AND [PERCHANGE-CUMOPENINTEREST] > 0) ) THEN [OPENINTERESTABSOLUTECHANGE] ELSE 0 END
		
	DECLARE @LongShort TABLE (ID INT IDENTITY(1,1), ProcessedDataId INT)
	
	INSERT INTO @LongShort
	SELECT ID FROM ProcessedData
	WHERE SCRIPNAME = @ScripName
	ORDER BY DATE ASC

	DECLARE @iterationLS INT = 1
	DECLARE @TotalCountLS INT= ( SELECT COUNT(1) FROM @LongShort )
	DECLARE @LongsTillNow INT = 0
	DECLARE @ShortsTilNow INT = 0
	DECLARE @TableId INT = 0

	WHILE (@iterationLS <= @TotalCountLS)
	BEGIN

		SET @TableId = (SELECT ProcessedDataId FROM @LongShort WHERE ID = @iterationLS)
		SET @LongsTillNow = @LongsTillNow + CAST((SELECT LONG FROM ProcessedData WHERE ID = @TableId) AS INT)
		SET @ShortsTilNow = @ShortsTilNow + CAST((SELECT SHORT FROM ProcessedData WHERE ID = @TableId) AS INT)

		UPDATE ProcessedData
		SET LONGSTILLNOW = @LongsTillNow , SHORTSTILLNOW = @ShortsTilNow
		WHERE ID = @TableId

		SET @iterationLS = @iterationLS + 1
	END

END
GO


USE [SharesData]
GO

/****** Object:  StoredProcedure [dbo].[UpdateEquityData]    Script Date: 1/19/2022 2:55:32 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

--DROP PROCEDURE dbo.UpdateEquityData

CREATE PROCEDURE [dbo].[UpdateEquityData]
	@IndexData [dbo].[IndexData] READONLY,
	@EquityData [dbo].[EquityData] READONLY,
	@FutureData [dbo].[FutureData] READONLY,
	@ScripName NVARCHAR(200),
	@IsEquityData BIT,
	@IsIndexData BIT
AS
BEGIN

	IF(@IsIndexData = 1)
	BEGIN

		INSERT INTO [dbo].[Equity]
		(
			[DATE] ,[SCRIPNAME] ,[SERIES] ,[OPEN] ,[HIGH] ,[LOW] ,[PREVCLOSE] ,[LTP] ,[CLOSE] 
			,[VWAP] ,[52WH] ,[52WL] ,[VOLUME] ,[VALUE] ,[NOOFTRADES]
		)
		SELECT eqd.[DATE] ,@ScripName ,'' ,eqd.[OPEN] ,eqd.[HIGH] ,eqd.[LOW] ,0 ,0 ,eqd.[CLOSE] 
			,0 ,0 ,0 ,0 ,0, 0
		FROM @IndexData eqd
			LEFT JOIN [Equity] eq ON eqd.DATE = eq.DATE AND eq.SCRIPNAME = @ScripName 
		WHERE eq.ID IS NULL
	END
	ELSE IF(@IsEquityData = 1)
	BEGIN

		INSERT INTO [dbo].[Equity]
		(
			[DATE] ,[SCRIPNAME] ,[SERIES] ,[OPEN] ,[HIGH] ,[LOW] ,[PREVCLOSE] ,[LTP] ,[CLOSE] 
			,[VWAP] ,[52WH] ,[52WL] ,[VOLUME] ,[VALUE] ,[NOOFTRADES]
		)
		SELECT eqd.[DATE] ,@ScripName ,eqd.[SERIES] ,eqd.[OPEN] ,eqd.[HIGH] ,eqd.[LOW] ,eqd.[PREVCLOSE] ,eqd.[LTP] ,eqd.[CLOSE] 
			,eqd.[VWAP] ,eqd.[52WH] ,eqd.[52WL] ,eqd.[VOLUME] ,eqd.[VALUE] ,eqd.[NOOFTRADES]
		FROM @EquityData eqd
			LEFT JOIN [Equity] eq ON eqd.DATE = eq.DATE AND eq.SCRIPNAME = @ScripName 
		WHERE eq.ID IS NULL
	END
	ELSE
	BEGIN
		INSERT INTO [dbo].[FutureData]
		(	
			[SCRIPNAME] ,[DATE] ,[EXPIRYDATE] ,[OPTIONTYPE] ,[STRIKEPRICE] ,[OPENPRICE]
				   ,[HIGHPRICE] ,[LOWPRICE] ,[CLOSEPRICE] ,[LASTPRICE] ,[SETTLEPRICE]
				   ,[VOLUME] ,[VALUE] ,[PREMIUMVALUE] ,[OPENINTEREST] ,[CHANGEINOI]
		)
		SELECT 
			@ScripName ,fdd.[DATE] ,fdd.[EXPIRYDATE] ,fdd.[OPTIONTYPE] ,fdd.[STRIKEPRICE] ,fdd.[OPENPRICE]
				   ,fdd.[HIGHPRICE] ,fdd.[LOWPRICE] ,fdd.[CLOSEPRICE] ,fdd.[LASTPRICE] ,fdd.[SETTLEPRICE]
				   ,fdd.[VOLUME] ,fdd.[VALUE] ,fdd.[PREMIUMVALUE] ,fdd.[OPENINTEREST] ,fdd.[CHANGEINOI]
		FROM @FutureData fdd
			LEFT JOIN [FutureData] fd ON fdd.DATE = fd.DATE AND fdd.EXPIRYDATE = fd.EXPIRYDATE AND fd.SCRIPNAME = @ScripName
		WHERE fd.ID IS NULL
	END
END
GO




