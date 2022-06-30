def double_scatter_bar(input_df,title,xs='surface',ys='smoothness',scolor=None,xh='count()',yh1='surface',yh2='smoothness',hcolor=None,fontsize=24):

    interval = alt.selection_interval()

    default_color = alt.value('lightseagreen')

    if not hcolor:
        hcolor = default_color

    if not scolor:
        scolor = default_color


    scatter = alt.Chart(input_df,title=title).mark_point().encode(
        x=xs,
        y=ys,
        color=scolor,
        tooltip=alt.Tooltip(['type','id']),
    ).add_selection(interval)

    hist_base = alt.Chart(input_df).mark_bar().encode(
        x=xh,
        color=hcolor,
        tooltip=alt.Tooltip(['type','id']),
        

    ).properties(
        width=300,
        height=220,
    ).transform_filter(
        interval,
    )

    # if hcolor:
    #      hist_base.encode(color=hcolor)

    hist = hist_base.encode(y=yh1) | hist_base.encode(y=yh2)

    return (scatter & hist).configure_title(fontSize=fontsize,align='center')