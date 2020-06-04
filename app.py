import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.express as px
import plotly
import plotly.graph_objects as go
import os
import json
import numpy as np
from plotly.subplots import make_subplots
from PIL import Image
from dash.dependencies import Input, Output, State


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

colors = {
    'background': '#ff00ff',
    'text': '#000000'
}

def zone(wayid, east, west, north, south):
    wayid = str(wayid)
    ans = 'None'
    count = 0
    if wayid in east:
        ans = 'east'
        count+=1
    if wayid in west:
        ans = 'west'
        count+=1
    if wayid in north:
        ans = 'north'
        count+=1
    if wayid in south:
        ans = 'south'
        count+=1
    return (ans, count)

def query_direction(x):
    start = ''
    end = ''
    current = ''
    bearing = None
    turnback = 0
    zones = 0
    for zone, bear in zip(x['int_zone'].values, x['bearing'].values):
        if zone[0] != 'None':
            if start == '':
                start = zone[0]
            else:
                end = zone[0]
            if zone[0] != current:
                zones += 1
            if bearing != None and (abs(bearing-bear) >= 90 and abs(bearing-bear) <= 270):
                turnback = 1
            bearing = bear
            current = zone[0]
    return (start, end, zones, turnback)

def f(x):
    d = {}
    direction = query_direction(x)
    d['start'] = direction[0]
    d['end'] = direction[1]
    d['zones'] = direction[2]
    d['turnback'] = direction[3]
    return pd.Series(d, index=['start', 'end', 'zones', 'turnback'])

def getTransformData(intersection, date_group_title, peaktime):
    file = 'screen/' + peaktime + '_peak_screen_' + intersection + '_' + date_group_title + '.csv'
    df = pd.read_csv(file)
    with open('ways/' + intersection + '_east_ways.txt', 'r') as filehandle:
        east = json.load(filehandle)
    with open('ways/' + intersection + '_west_ways.txt', 'r') as filehandle:
        west = json.load(filehandle)
    with open('ways/' + intersection + '_north_ways.txt', 'r') as filehandle:
        north = json.load(filehandle)
    with open('ways/' + intersection + '_south_ways.txt', 'r') as filehandle:
        south = json.load(filehandle)
    if peaktime == 'morning':
        start_time = '07:00:00' 
        end_time = '09:00:00'
    elif peaktime == 'evening':
        start_time = '16:00:00' 
        end_time = '18:00:00'
    df_filter = df[(df['time'] >= start_time) & (df['time'] <= end_time)]
    df_filter['int_zone'] = df_filter.apply(lambda x: zone(x['wayids'], east, west, north, south), axis = 1)
    #df_filter['int_zone_count'] = df_filter.apply(lambda x: x['int_zone'][1], axis = 1)
    df_zoned = df_filter.sort_values(by = ['driverid', 'bookingcode', 'date'])[['driverid','bookingcode','wayids','bearing','int_zone','date']]
    df_direction = df_zoned.groupby(['driverid','bookingcode']).apply(f)
    df_direction_filter = df_direction[ ((df_direction['zones']==2) & (df_direction['start']!=df_direction['end'])) |
                                    ((df_direction['zones']==1) & (df_direction['start']==df_direction['end']) & (df_direction['turnback'] == 1)) ]
    df_direction_group = df_direction_filter.groupby(['start','end'], as_index = True).size().to_frame('count')
    directions = ['east','north','south','west']
    for j in directions:
        for k in directions:
             if (j,k) not in df_direction_group.index :
                idx = (j,k)
                df_direction_group.loc[(j,k),'count'] = int(0)
    df_direction_group['count'] = df_direction_group['count'].astype(np.int64)
    return df_direction_group.reset_index()


def getReadyData(intersection, date_group_title, peaktime):
#     if date_group_title == 'all_weekend' and peaktime == 'morning' and intersection in ['witthayu','expy','qsncc']:
#         df = getTransformData(intersection, date_group_title, peaktime).reset_index()
#     else:
#         df = pd.read_csv('csv/through_csv_'+ intersection + '_' + date_group_title + '_' + peaktime +'.csv')
    df = pd.read_csv('csv/through_csv_'+ intersection + '_' + date_group_title + '_' + peaktime +'.csv')
    df['exist'] = True
    if intersection == 'expy':
        not_exist = [('north','south'), ('north', 'north'), ('south', 'north'), ('south', 'east'), ('east','north'), ('east','east'), ('west','west')]
        for i in not_exist:
            df.loc[(df['start']==i[0])&(df['end']==i[1]),'exist'] = False
    countList = list()
    countPercent = list()
    countPercentDir = list()
    existence = list()
    csum = df[df['exist']==True].sum(axis = 0)['count']
    direction = ['east','north','south','west']
    days_per_group = {'all_weekday' : 21, 'all_weekend' : 9, 'normal_monday': 3, 'normal_friday' : 4}
    for i in direction:
          for j in direction:
                countList.append(df[(df['start']==i)&(df['end']==j)]['count'].item()/days_per_group[date_group_title])
                countPercent.append((df[(df['start']==i)&(df['end']==j)]['count'].item())*100/csum)
                countPercentDir.append((df[(df['start']==i)&(df['end']==j)]['count'].item())*100/df[(df['start']==i)&(df['exist']==True)].sum(axis = 0)['count'])
                existence.append(df[(df['start']==i)&(df['end']==j)]['exist'].item())
    return countList, countPercent, countPercentDir, existence 

def gentitle(intersection, date_group_title, peaktime):
    if peaktime == 'morning':
        start_time = '07:00' 
        end_time = '09:00'
    elif peaktime == 'evening':
        start_time = '16:00' 
        end_time = '18:00'
    q_intersection = intersection
    if q_intersection == 'qsncc':
        q_intersection = 'rama 4'
    return  'Intersection: %s<br>%s                     %s(%s - %s)' % (q_intersection.title(),date_group_title.replace('_', ' ').title(),peaktime.title(),start_time, end_time)


def genQueueLengthData(intersection, date_group_title, peaktime):
    alt_intersection = intersection
    if alt_intersection == 'qsncc':
        alt_intersection = 'ramaiv'
    queue_length_file = 'queue_csv/%s_queue_length_%s.csv' % (alt_intersection, date_group_title)
    ql_df = pd.read_csv(queue_length_file)
    ql_df.rename(columns = {'Unnamed: 0': 'time'}, inplace = True)
    if peaktime == 'morning':
        start_time = '07:00' 
        end_time = '09:00'
    elif peaktime == 'evening':
        start_time = '16:00' 
        end_time = '18:00'
    ql_df_filter = ql_df[(ql_df['time']>=start_time) & (ql_df['time']<end_time)]
    ql_df_group = ql_df_filter.groupby(['direction']).mean() 
    return ql_df_group

def genqlentext(vert, val):
    if(vert == True):
        return  'Queue Length:<br>%.1f m'% val
    if(vert == False):
        return  'Queue<br>Length:<br>%.1f m'% val
    
def gentext(num, countList, countPercent, vert, exist):
    if(exist == False):
        return 'N/A'
    if(vert == False):
        return '%.1f'%countList[num] + ' (%.1f%%)'%countPercent[num] 
    if(vert == True):
        return '%.1f'%countList[num] + '<br>%.1f%%'%countPercent[num] 

def genPhaseLane(num, countList, countPercent, vert, exist, intersection):
    df = pd.read_csv('phase_csv/' + intersection + '_phase.csv')
    phase = df.loc[num]['phase']
    lanes = df.loc[num]['lanes']
    if(vert == False):
        return ('%.1f L'% lanes if lanes != 0 else '') + (' / ' if (lanes != 0 and phase != 0) else '') + ('P %d' % phase if phase != 0 else '')
    if(vert == True):
        return ('%.1f L'% lanes if lanes != 0 else '') + ('<br>' if (lanes != 0 and phase != 0) else '') + ('P %d' % phase if phase != 0 else '')

def genAnnotations(intersection, date_group_title, peaktime, countList, countPercent, existence):
    title_font = dict(
                    family='Arial',
                    size=18,
                    color = '#000000'
                    )
    info_font = dict(
                    family='Arial',
                    size=12,
                    color = '#000000'
                    )
    pos = [(825,540), (825,605), (825,735), (825,670),
           (675,240), (480,240), (610,240), (545,240),
           (530,920), (465,920), (595,920), (400,920),
           (250,505), (250,440), (250,570), (250,635)]
    xalign = ['left', 'center', 'center', 'right']      
    vert = [False, True, True, False]
    queue_length_df = genQueueLengthData(intersection, date_group_title, peaktime)
    
    annotations = [dict(
            align = 'center',
            font = info_font,
            showarrow = False,
            text = gentext(i, countList, countPercent, vert[i//4], existence[i]),
            x = pos[i][0]/1080,
            xanchor = xalign[i//4],
            xref = 'paper',
            y = 1 - pos[i][1]/1080,
            yanchor = 'middle',
            yref = 'paper'
                  ) for i in range(16)]
    
    annotations.append(dict(
            align = 'center',
            font = title_font,
            showarrow = False,
            text = gentitle(intersection, date_group_title, peaktime),
            x = 540/1080,
            xanchor = 'center',
            xref = 'paper',
            y = 1 - 60/1080,
            yanchor = 'middle',
            yref = 'paper'
                  ))
    qlenpos = [(1010,635), (580,160), (500,990), (65,535)]
    direction = ['east','north','south','west']
    annotations.extend([dict(
            align = 'center',
            font = info_font,
            showarrow = False,
            text = genqlentext(vert[i], queue_length_df.loc[direction[i]].dist),
            x = qlenpos[i][0]/1080,
            xanchor = 'center',
            xref = 'paper',
            y = 1 - qlenpos[i][1]/1080,
            yanchor = 'middle',
            yref = 'paper'
                  ) for i in range(4)])
    
    return annotations

def gencolor(num, n_exist_direction):
    if(num >= 300/n_exist_direction):
        return 'rgb(192,0,0)'
    elif(num >= 200/n_exist_direction):
        return 'rgb(192,96,0)'
    elif(num >= 100/n_exist_direction):
        return 'rgb(192,192,0)'
    return 'rgb(0,192,0)'

def genLines(countList, countPercent, existence):
    positions = [((700,510),(700,560)),
                 ((700,575),(700,625)),
                 ((700,705),(700,755)),
                 ((700,640),(700,690)),
                 ((645,420),(695,420)),
                 ((450,420),(500,420)),
                 ((580,420),(630,420)),
                 ((515,420),(565,420)),
                 ((500,755),(550,755)),
                 ((435,755),(485,755)),
                 ((565,755),(615,755)),
                 ((370,755),(420,755)),
                ((380,490),(380,540)),
                ((380,425),(380,475)),
                ((380,555),(380,605)),
                ((380,620),(380,675))]
    n_exist_direction = existence.count(True) 
    
    shapes = [ dict(
                type = 'line',
                line = dict(
                    color = gencolor(countPercent[i], n_exist_direction),
                    dash = 'solid',
                    width = 5),
                x0 = positions[i][0][0]/1080,
                x1 = positions[i][1][0]/1080,
                xref = 'paper',
                y0 = 1- positions[i][0][1]/1080,
                y1 = 1- positions[i][1][1]/1080,
                yref = 'paper'
                ) for i in range(16) if existence[i]==True]
        
    return shapes

def make_traffic_fig(intersection, peaktime, date_group_title, percent_by):
    countList, countPercent, countPercentDir, existence = getReadyData(intersection, date_group_title, peaktime)
    if percent_by == 'all':
        all_annotations = genAnnotations(intersection, date_group_title, peaktime, countList, countPercent, existence)
    elif percent_by == 'each_incoming':
        all_annotations = genAnnotations(intersection, date_group_title, peaktime, countList, countPercentDir, existence)
    else:
        all_annotations = genAnnotations(intersection, date_group_title, peaktime, countList, countPercent, existence)

    img = Image.open("pic/intersection_map_jpg.jpg")
    fig = go.Figure(
            layout = go.Layout(
                xaxis = go.layout.XAxis(
                    showticklabels = False,
                    showgrid=False,
                    zeroline=False,
                    range = [0, 1080]
                ),
                yaxis = go.layout.YAxis(
                    showticklabels = False,
                    showgrid=False,
                    zeroline=False,
                    range = [0, 1080],
                    scaleanchor = 'x'
                ),
                 autosize=False,
                 height= 630,
                 width= 630,
                 margin = {'l': 0, 'r': 0, 't': 0, 'b': 0},
                 images= [dict(
                    source= img,
                    x=0,
                    sizex=1,
                    y=1,
                    sizey=1,
                    xref="paper",
                    yref="paper",
                    opacity=1.0,
                    layer="above",
                    sizing="stretch"
                )],
                annotations = all_annotations,
                shapes = genLines(countList, countPercent, existence)
             )
    )
    return fig

radioPanelStyle = {
                             'backgroundColor' : 'rgb(0,0,0)',
                             'border-radius' : 10,
                             'border' : '5px solid black',
                             'padding' : 12,
                             'margin-left' : 'auto',
                             'margin-right' : 'auto',
                             'margin-bottom' : 10,
                             'width' : '35%',
                  }

radioHeaderStyle = {
                             'padding-bottom' : 10,
                             'color' : 'white',
                             'text-align' : 'center'
                   }
radioItemPanelStyle = {
                                    'backgroundColor' : 'rgb(255,255,255)',
                                    'border-bottom-left-radius' : 10,
                                    'border-bottom-right-radius' : 10,
                                    'padding' : 10,
                                    'text-align' : 'left'
                 }
radioItemLabelStyle = {
                                    'display' : 'block',
                                    'margin' : 5
                      }

app.layout = html.Div(style={'backgroundColor': colors['background'],
                             'text-align' : 'center',
                             'width' : 1370,
                             'margin' : 'auto' #horizontal center
                            }, 
                      children = [
        #right
        html.Div( 
            style={'padding-left' : 10,
                   'padding-top' : -20,
                   'padding-bottom' : 10,
                   'padding-right' : 10,
                   'border-style' : 'solid',
                   'border-width' : 3,
                   'width' : 630,
                   'float' : 'right'
                   },
            children = [
                dcc.Graph(
                   id='traffic-fig',
                   figure = make_traffic_fig('witthayu', 'morning', 'all_weekday', 'all')
                )] 
        ),
        #left
        html.Div(
            style = {
                 'width' : 700,
                 'float' : 'left',
                 'font-family': 'arial',
                 'border-style' : 'solid',
                 'border-width' : 3,
                 'display' : 'flex',
                 'flex-wrap' : 'wrap',
                 'text-align' : 'center',
                    },
            children = [
                    html.Div(
                            children='Rama IV Road Traffic Analysis',
                            style={
                                'textAlign': 'center',
                                'font-family': 'arial',
                                'color': colors['text'],
                                'margin' : 'auto',
                                'padding' : 10,
                                'font-size' : 24
                            }
                      ),
                    html.Div(
                             children='Total counts of Grab Taxis for each group of date in the peak time.', 
                             style={
                            'textAlign': 'center',
                            'font-family': 'arial',
                            'color': colors['text'],
                            'margin' : 'auto',
                            'padding' : 10,
                            'font-size' : 20
                    }),
                    
                    html.Div(style = {
                            'display' : 'flex',
                            'flex-wrap' : 'wrap',
                            'margin' : 'auto',
                            'padding-left' : '5%',
                            'padding-right' : '5%',
                            'padding-top' : 20,
                            'border-style' : 'solid'
                                     }, 
                             children = [
                            html.Div(style = radioPanelStyle,
                                     children = [
                                        html.Div(style = radioHeaderStyle,
                                                 children = 'Intersection'),
                                        html.Div(style = radioItemPanelStyle,
                                                 children = [dcc.RadioItems(
                                                        id='intersection',
                                                        options = [
                                                            {'label': 'Witthayu', 'value': 'witthayu'},
                                                            {'label': 'Expressway', 'value': 'expy'},
                                                            {'label': 'Rama 4', 'value': 'qsncc'}
                                                            ],
                                                        value = 'witthayu',
                                                        labelStyle= radioItemLabelStyle
                                                )])
                                     ]),
                            
                        
                            html.Div(style = radioPanelStyle,
                                     children = [
                                        html.Div(style = radioHeaderStyle,
                                                 children = 'Show percent values of'),
                                        html.Div(style = radioItemPanelStyle,
                                                 children = [dcc.RadioItems(
                                                        id='percent-by',
                                                        options = [
                                                            {'label': 'All directions', 'value': 'all'},
                                                            {'label': 'Each incoming direction', 'value': 'each_incoming'}
                                                        ],
                                                        value = 'all',
                                                        labelStyle= radioItemLabelStyle
                                                )])
                                     ]),
                            
                            html.Div(style = radioPanelStyle,
                                     children = [
                                        html.Div(style = radioHeaderStyle,
                                                 children = 'Group of Day'),
                                        html.Div(style = radioItemPanelStyle, 
                                                 children = [dcc.RadioItems(
                                                        id='date_group_title',
                                                        options = [
                                                            {'label': 'All weekdays', 'value': 'all_weekday'},
                                                            {'label': 'All weekends', 'value': 'all_weekend'},
                                                            {'label': 'Normal Mondays', 'value': 'normal_monday'},
                                                            {'label': 'Normal Fridays', 'value': 'normal_friday'}
                                                            ],
                                                        value = 'all_weekday',
                                                        labelStyle = radioItemLabelStyle
                                                )])
                                     ]),
                        
                            html.Div(style = radioPanelStyle,
                                     children = [
                                        html.Div(style = radioHeaderStyle,
                                                 children = 'Peak Time'),
                                        html.Div(style = radioItemPanelStyle,
                                                 children = [dcc.RadioItems(
                                                        id='peaktime',
                                                        options = [
                                                            {'label': 'Morning', 'value': 'morning'},
                                                            {'label': 'Evening', 'value': 'evening'}
                                                            ],
                                                        value = 'morning',
                                                        labelStyle = radioItemLabelStyle
                                                 )])
                                     ])
                            ]),
                   
                    html.Div(style = {
                            'width' : '100%',
                            'margin' : 20
                            },
                             children = [
                                html.Button('Update Figure', id='figure_button', n_clicks=0,
                                    style = {
                                      'margin' : 'auto',
                                      'padding' : 10,
                                      'font-size' : 20,
                                      'width' : '30%',
                                      'font-family': 'arial'
                                   })
                             ])
                   ])
         #left-end
        ])
    
@app.callback(Output('traffic-fig', 'figure'),
              [Input('figure_button', 'n_clicks')],
              [State('intersection', 'value'),
               State('peaktime', 'value'),
               State('date_group_title', 'value'),
               State('percent-by', 'value')])
def update_traffic_fig(n, intersection, peaktime, date_group_title, percent_by):
    return make_traffic_fig(intersection, peaktime, date_group_title, percent_by)


if __name__ == '__main__':
    app.run_server(debug=True)