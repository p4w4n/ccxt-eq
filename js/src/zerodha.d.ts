import Exchange from './abstract/zerodha.js';
import type { Int, OrderSide, OrderType, Trade, OHLCV, Order, Str, Ticker, Balances, Tickers, Market, Dict, int, Num } from './base/types.js';
/**
 * @class zerodha
 * @augments Exchange
 * @description Zerodha Kite Connect API v3 implementation for CCXT
 *
 * This implementation follows the comprehensive integration guide for Zerodha Kite Connect
 * with Freqtrade. It provides a stateful session manager to handle daily token expiration
 * and maps Indian equity trading to the CCXT unified API.
 *
 * Symbol Convention: {EXCHANGE}:{TRADINGSYMBOL}/{CURRENCY}
 * Example: NSE:INFY/INR (Infosys on NSE in Indian Rupees)
 *
 * Authentication: Uses a daily-expiring access_token managed through a separate
 * generate_token.py script due to Zerodha's manual login requirement.
 */
export default class zerodha extends Exchange {
    describe(): any;
    fetchMarkets(params?: {}): Promise<Market[]>;
    fetchTicker(symbol: string, params?: {}): Promise<Ticker>;
    parseTicker(ticker: Dict, market?: Market): Ticker;
    fetchTickers(symbols?: string[], params?: {}): Promise<Tickers>;
    fetchOHLCV(symbol: string, timeframe?: string, since?: Int, limit?: Int, params?: {}): Promise<OHLCV[]>;
    parseOHLCV(ohlcv: any[], market?: Market, timeframe?: string, since?: Int, limit?: Int): OHLCV;
    fetchBalance(params?: {}): Promise<Balances>;
    createOrder(symbol: string, type: OrderType, side: OrderSide, amount: number, price?: Num, params?: {}): Promise<Order>;
    cancelOrder(id: string, symbol?: Str, params?: {}): Promise<Order>;
    fetchOrder(id: string, symbol?: Str, params?: {}): Promise<Order>;
    fetchOpenOrders(symbol?: Str, since?: Int, limit?: Int, params?: {}): Promise<Order[]>;
    fetchClosedOrders(symbol?: Str, since?: Int, limit?: Int, params?: {}): Promise<Order[]>;
    fetchMyTrades(symbol?: Str, since?: Int, limit?: Int, params?: {}): Promise<Trade[]>;
    parseOrder(order: Dict, market?: Market): Order;
    parseTrade(trade: Dict, market?: Market): Trade;
    sign(path: string, api?: string, method?: string, params?: {}, headers?: any, body?: any): any;
    handleErrors(code: int, reason: string, url: string, method: string, headers: Dict, body: string, response: any, requestHeaders: any, requestBody: any): any;
}
