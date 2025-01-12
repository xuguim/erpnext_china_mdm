
def run():
    import frappe,json
    from sqlalchemy import create_engine
    import pandas as pd
    cache = frappe.cache()

    year = '2024'
    month = '12'
    oa_db_info = frappe.get_doc('oa_db_info')
    engine_oa_msyql = create_engine(oa_db_info.oa_db_sqlalchemy)


    sql = f"""select usernameid,sum(total_money) as amount from xinhu_prodhj_goods_detail
    where prodhj_id in (select id from xinhu_prodhj 
    where year(applydt) = '{year}' and month(applydt) = '{month}' and isturn = 1 and status = 1)
    and total_money >0
    group by usernameid """
    df = pd.read_sql(sql,con=engine_oa_msyql)

    #匹配上工号
    oa_employee_number = frappe.db.get_list('Employee',
            fields=['employee_number','name'],
            as_list=True
        )
    df_ = pd.DataFrame(oa_employee_number,columns=['employee_number','name'])
    df_.drop_duplicates('employee_number',inplace=True)
    df_ = df_[~df_.employee_number.isna()]
    df.usernameid = df.usernameid.astype(str)
    df.merge(df_, how='inner',left_on='usernameid',right_on='employee_number')
    data = dict(zip(df.name, df.amount))

    cache.set('hrms_薪资构成项_计件工资数据缓存', json.dumps(data))