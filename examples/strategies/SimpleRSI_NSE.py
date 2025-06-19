# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class SimpleRSI_NSE(IStrategy):
    """
    A simple RSI strategy for Indian Equities on the NSE.
    
    This strategy demonstrates how to use the Zerodha CCXT wrapper
    with Freqtrade for automated trading of Indian stocks.
    
    Entry Signal: RSI crosses above 30 (oversold condition ending)
    Exit Signal: RSI crosses below 70 (overbought condition)
    
    Risk Management: 10% stop loss, tiered profit taking
    """
    
    # Strategy interface version - must be 2 or 3
    INTERFACE_VERSION = 3

    # Minimal ROI table - profit taking strategy
    minimal_roi = {
        "0": 0.10,   # 10% profit target
        "60": 0.05,  # 5% after 60 minutes
        "120": 0.02, # 2% after 120 minutes
        "240": 0.01  # 1% after 240 minutes (exit almost everything)
    }

    # Stoploss - risk management
    stoploss = -0.10  # 10% stop loss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.02  # 2%
    trailing_stop_positive_offset = 0.03  # 3%
    trailing_only_offset_is_reached = True

    # Timeframe for analysis
    timeframe = '1h'

    # Process only new candles
    process_only_new_candles = True

    # Startup period (number of candles needed for indicators)
    startup_candle_count: int = 30

    # Optional order type mapping
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
    }

    # Optional order time in force
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc',
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds all necessary indicators to the given DataFrame.
        
        This method is called for each pair in the whitelist and calculates
        the technical indicators needed for the strategy.
        """
        # RSI (Relative Strength Index)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Simple Moving Averages for trend confirmation
        dataframe['sma_20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        
        # Bollinger Bands for volatility assessment
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        
        # Volume indicators
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        
        # ATR for volatility-based position sizing (future enhancement)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe.
        
        Entry conditions:
        1. RSI crosses above 30 (oversold condition ending)
        2. Price is above 20-period SMA (short-term uptrend)
        3. Volume is above average (confirmation)
        4. Price is not too close to upper Bollinger Band (avoid buying peaks)
        """
        dataframe.loc[
            (
                # RSI condition - emerging from oversold
                (qtpylib.crossed_above(dataframe['rsi'], 30)) &
                
                # Trend condition - price above short-term moving average
                (dataframe['close'] > dataframe['sma_20']) &
                
                # Volume confirmation - above average volume
                (dataframe['volume'] > dataframe['volume_sma']) &
                
                # Avoid buying at peaks - not too close to upper Bollinger Band
                (dataframe['close'] < dataframe['bb_upperband'] * 0.98) &
                
                # Basic volume check
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe.
        
        Exit conditions:
        1. RSI crosses below 70 (overbought condition)
        2. Price touches or exceeds upper Bollinger Band
        3. Volume confirmation
        """
        dataframe.loc[
            (
                # RSI condition - entering overbought territory
                (qtpylib.crossed_below(dataframe['rsi'], 70)) |
                
                # Price at upper Bollinger Band (take profits)
                (dataframe['close'] >= dataframe['bb_upperband']) |
                
                # Alternative exit: price falls below 20-period SMA (trend change)
                (qtpylib.crossed_below(dataframe['close'], dataframe['sma_20']))
            ) &
            
            # Volume confirmation
            (dataframe['volume'] > 0),
            
            'exit_long'] = 1
            
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, current_time,
                           entry_tag, side: str, **kwargs) -> bool:
        """
        Called right before placing a entry order.
        Timing specification (note: current_time will always be set)
        
        This method can be used to add additional entry confirmations
        or to prevent trades during certain market conditions.
        
        For Indian markets, we might want to avoid trading:
        - During first 15 minutes of market open (high volatility)
        - During last 30 minutes of market close (erratic movements)
        - During major news events or economic announcements
        """
        
        # Get current time in IST (Indian Standard Time)
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        current_time_ist = current_time.astimezone(ist)
        current_hour = current_time_ist.hour
        current_minute = current_time_ist.minute
        
        # Avoid trading in first 15 minutes of market open (9:15 AM IST)
        if current_hour == 9 and current_minute < 30:
            return False
        
        # Avoid trading in last 30 minutes before market close (3:30 PM IST)
        if current_hour == 15 and current_minute >= 0:
            return False
        
        # Only trade during market hours (9:15 AM to 3:30 PM IST)
        if current_hour < 9 or (current_hour == 9 and current_minute < 15):
            return False
        if current_hour > 15 or (current_hour == 15 and current_minute > 30):
            return False
        
        return True

    def custom_entry_price(self, pair: str, current_time, proposed_rate: float,
                          entry_tag, side: str, **kwargs) -> float:
        """
        Custom entry price logic.
        
        For Indian equities, we might want to:
        - Place limit orders slightly below market price for better fills
        - Adjust for tick size constraints
        """
        
        # Place buy orders 0.1% below proposed rate for better fills
        if side == 'long':
            return proposed_rate * 0.999
        
        return proposed_rate

    def custom_exit_price(self, pair: str, trade, current_time,
                         proposed_rate: float, current_profit: float, **kwargs) -> float:
        """
        Custom exit price logic.
        
        For Indian equities, we might want to:
        - Place limit orders slightly above market price for exits
        - Implement more aggressive exit pricing during high volatility
        """
        
        # Place sell orders 0.1% above proposed rate for better fills
        return proposed_rate * 1.001

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached.
        
        For Indian equity trading, we might want to monitor:
        - NIFTY 50 index for overall market sentiment
        - Sector indices for sector-specific strategies
        """
        return [
            # Monitor NIFTY 50 index on different timeframes
            ('NSE:NIFTY50/INR', '1h'),
            ('NSE:NIFTY50/INR', '1d'),
            # Add other relevant indices or large-cap stocks for market context
        ]

    def leverage(self, pair: str, current_time, current_rate: float,
                proposed_leverage: float, max_leverage: float, entry_tag,
                side: str, **kwargs) -> float:
        """
        Customize leverage for each new trade.
        
        For Indian equities with Zerodha:
        - CNC (Cash and Carry) products don't use leverage
        - MIS (Margin Intraday Square-off) products have leverage
        """
        
        # For equity delivery trades, no leverage
        return 1.0
