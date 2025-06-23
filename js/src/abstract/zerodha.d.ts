import { implicitReturnType } from '../base/types.js';
import { Exchange as _Exchange } from '../base/Exchange.js';
interface Exchange {
    publicGetInstruments(params?: {}): Promise<implicitReturnType>;
    publicGetInstrumentsExchange(params?: {}): Promise<implicitReturnType>;
    publicGetQuote(params?: {}): Promise<implicitReturnType>;
    publicGetQuoteLtp(params?: {}): Promise<implicitReturnType>;
    publicGetQuoteOhlc(params?: {}): Promise<implicitReturnType>;
    privateGetUserProfile(params?: {}): Promise<implicitReturnType>;
    privateGetUserMargins(params?: {}): Promise<implicitReturnType>;
    privateGetUserMarginsSegment(params?: {}): Promise<implicitReturnType>;
    privateGetPortfolioPositions(params?: {}): Promise<implicitReturnType>;
    privateGetPortfolioHoldings(params?: {}): Promise<implicitReturnType>;
    privateGetOrders(params?: {}): Promise<implicitReturnType>;
    privateGetOrdersOrderId(params?: {}): Promise<implicitReturnType>;
    privateGetTrades(params?: {}): Promise<implicitReturnType>;
    privateGetTradesOrderId(params?: {}): Promise<implicitReturnType>;
    privateGetInstrumentsHistoricalInstrumentTokenInterval(params?: {}): Promise<implicitReturnType>;
    privatePostOrdersVariety(params?: {}): Promise<implicitReturnType>;
    privatePostOrdersVarietyOrderId(params?: {}): Promise<implicitReturnType>;
    privatePostPortfolioPositions(params?: {}): Promise<implicitReturnType>;
    privatePutOrdersVarietyOrderId(params?: {}): Promise<implicitReturnType>;
    privateDeleteOrdersVarietyOrderId(params?: {}): Promise<implicitReturnType>;
}
declare abstract class Exchange extends _Exchange {
}
export default Exchange;
