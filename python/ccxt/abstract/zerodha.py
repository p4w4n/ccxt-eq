from ccxt.base.types import Entry


class ImplicitAPI:
    public_get_instruments = publicGetInstruments = Entry('instruments', 'public', 'GET', {})
    public_get_instruments_exchange = publicGetInstrumentsExchange = Entry('instruments/{exchange}', 'public', 'GET', {})
    public_get_quote = publicGetQuote = Entry('quote', 'public', 'GET', {})
    public_get_quote_ltp = publicGetQuoteLtp = Entry('quote/ltp', 'public', 'GET', {})
    public_get_quote_ohlc = publicGetQuoteOhlc = Entry('quote/ohlc', 'public', 'GET', {})
    private_get_user_profile = privateGetUserProfile = Entry('user/profile', 'private', 'GET', {})
    private_get_user_margins = privateGetUserMargins = Entry('user/margins', 'private', 'GET', {})
    private_get_user_margins_segment = privateGetUserMarginsSegment = Entry('user/margins/{segment}', 'private', 'GET', {})
    private_get_portfolio_positions = privateGetPortfolioPositions = Entry('portfolio/positions', 'private', 'GET', {})
    private_get_portfolio_holdings = privateGetPortfolioHoldings = Entry('portfolio/holdings', 'private', 'GET', {})
    private_get_orders = privateGetOrders = Entry('orders', 'private', 'GET', {})
    private_get_orders_order_id = privateGetOrdersOrderId = Entry('orders/{order_id}', 'private', 'GET', {})
    private_get_trades = privateGetTrades = Entry('trades', 'private', 'GET', {})
    private_get_trades_order_id = privateGetTradesOrderId = Entry('trades/{order_id}', 'private', 'GET', {})
    private_get_instruments_historical_instrument_token_interval = privateGetInstrumentsHistoricalInstrumentTokenInterval = Entry('instruments/historical/{instrument_token}/{interval}', 'private', 'GET', {})
    private_post_orders_variety = privatePostOrdersVariety = Entry('orders/{variety}', 'private', 'POST', {})
    private_post_orders_variety_order_id = privatePostOrdersVarietyOrderId = Entry('orders/{variety}/{order_id}', 'private', 'POST', {})
    private_post_portfolio_positions = privatePostPortfolioPositions = Entry('portfolio/positions', 'private', 'POST', {})
    private_put_orders_variety_order_id = privatePutOrdersVarietyOrderId = Entry('orders/{variety}/{order_id}', 'private', 'PUT', {})
    private_delete_orders_variety_order_id = privateDeleteOrdersVarietyOrderId = Entry('orders/{variety}/{order_id}', 'private', 'DELETE', {})
