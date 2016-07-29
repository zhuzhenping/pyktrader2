import misc
import agent
import sys
import data_handler as dh
import pandas as pd
import numpy as np
import strategy as strat
import datetime
import backtest

def fisher_swing_sim( mdf, config):
    pos_class = config['pos_class']
    pos_args  = config['pos_args']
    pos_update = config.get('pos_update', False)
    offset = config['offset']
    close_daily = config['close_daily']
    tcost = config['trans_cost']
    unit = config['unit']
    freq = config['freq']
    win = config['param']
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols=['contract'])
    fisher = dh.FISHER(xdf, win[0])
    xdf['FISHER_I'] = fisher['FISHER_I'].shift(1)
    xdf = xdf.join(dh.BBANDS_STOP(xdf, win[1], 1.0).shift(1))
    ha_df = dh.HEIKEN_ASHI(xdf, win[2]).shift(1)
    xdf['HAopen'] = ha_df['HAopen']
    xdf['HAclose'] = ha_df['HAclose']
    xdf['prev_close'] = xdf['close'].shift(1)
    xdf['close_ind'] = np.isnan(xdf['close'].shift(-1))
    if close_daily:
        daily_end = (xdf['date']!=xdf['date'].shift(-1))
        xdf['close_ind'] = xdf['close_ind'] | daily_end        
    ll = xdf.shape[0]
    xdf['pos'] = pd.Series([0]*ll, index = df.index)
    xdf['cost'] = pd.Series([0]*ll, index = df.index)
    curr_pos = []
    closed_trades = []
    end_d = df.index[-1].date()
    tradeid = 0
    for idx, dd in enumerate(xdf.index):
        mslice = xdf.loc[dd]
        min_id = mslice.min_id
        d = dd.date()
        if len(curr_pos) == 0:
            pos = 0
        else:
            pos = curr_pos[0].pos
        df.ix[dd, 'pos'] = pos
        if np.isnan(mslice.BBSTOP_lower) or np.isnan(mslice.FISHER_I) or np.isnan(mslice.HAclose):
            continue
        end_trading = (min_id >=config['exit_min']) and (d == end_d)
        stop_loss = (pos > 0) and ((mslice.close < mslice.BBSTOP_lower) or (mslice.FISHER_I<0))
        stop_loss = stop_loss or ((pos < 0) and ((mslice.close > mslice.BBSTOP_upper) or (mslice.FISHER_I>0)))
        start_long = (mslice.FISHER_I>0) and (mslice.HAclose > mslice.HAopen ) and (mslice.BBSTOP_trend > 0)
        start_short = (mslice.FISHER_I<0) and (mslice.HAclose < mslice.HAopen ) and (mslice.BBSTOP_trend < 0)
        if pos != 0:
            if stop_loss or end_trading:
                curr_pos[0].close(mslice.close - misc.sign(pos) * offset , dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                df.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)    
                pos = 0
            pos = (start_long == True) * unit - (start_short == True) * unit
            if abs(pos)>0:
                #target = (start_long == True) * mslice.close +(start_short == True) * mslice.close
                new_pos = strat.TradePos([mslice.contract], [1], pos, mslice.close, mslice.close)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(mslice.close + misc.sign(pos)*offset, dd)
                curr_pos.append(new_pos)
                xdf.set_value(dd, 'cost', abs(pos) * (offset + mslice.close*tcost))
        xdf.ix[dd, 'pos'] = pos
    return (xdf, closed_trades)
    
def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_fisher_swing.fisher_swing_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'fisherswing_test'
    sim_config['products']   = ['rb', 'i', 'j', 'jm', 'ZC', 'ru', 'ni', 'y', 'p', 'm', 'RM', 'cs', 'jd', 'a', 'l', 'pp', 'TA', 'MA', 'bu', 'cu', 'al', 'ag', 'au']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160708'
    sim_config['need_daily'] = False
    sim_config['freq'] = ['3min', '5min', '15min', '30min', '60min']
    sim_config['param'] = [ [5,  10, 20], [5, 10, 40], [5, 20, 40], [5, 20, 80], \
                             [10, 20, 40], [10, 20, 80],[10, 30, 60],[10, 30, 120],\
                             [10, 40, 80], [10, 40, 120],\
                             [5, 10], [5, 20], [5, 40], \
                             [10, 20], [10, 30], [10, 40] ]
    sim_config['pos_class'] = 'strat.TradePos'
    #sim_config['pos_class'] = 'strat.ParSARTradePos'
    #sim_config['pos_args'] = [{'reset_margin': 1, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 2, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 3, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 1, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
    #                            {'reset_margin': 2, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
    #                            {'reset_margin': 3, 'af': 0.01, 'incr': 0.01, 'cap': 0.2}]
    sim_config['offset']    = 1
    config = {'capital': 10000,
              'trans_cost': 0.0,
              'unit': 1,
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'exit_min': 2055,
              'pos_args': {},
              }
    sim_config['config'] = config
    with open(filename, 'w') as outfile:
        json.dump(sim_config, outfile)
    return sim_config
    
if __name__=="__main__":
    args = sys.argv[1:]
    if len(args) < 1:
        print "need to input a file name for config file"
    else:
        gen_config_file(args[0])
    pass
