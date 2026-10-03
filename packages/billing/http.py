"""Small authenticated billing API projection; no public receipt parser."""
from packages.billing.contracts import BillingError
from packages.billing.postgres import BillingActor
from packages.store.ledger import Fault


def public_order(row):
    # Never expose tenant/session identifiers, merchant transaction identifiers,
    # verification evidence or adapter internals to the ordinary UI.
    fields=('order_id','plan_id','plan_version','product_id','currency','amount_minor',
            'duration_days','max_requests','state','verification_state','created_at','expires_at')
    result={key:row[key] for key in fields}
    result['max_cost_cny']=str(row['max_cost_cny'])
    result['temporary']=row['temporary_enabled'];result['persistent']=row['persistent_enabled']
    for key in ('access_starts_at','access_expires_at','access_enabled'):
        if row.get(key) is not None:result[key]=row[key]
    return result


def dispatch(application,method,path,data=None):
    if not getattr(application,'member_context',None):raise Fault(403,'普通账号登录后可查看会员与订单')
    service=getattr(application,'billing',None)
    actor=BillingActor(*application.member_context)
    try:
        if method=='GET' and path=='/v1/billing/catalog':
            return service.catalog(actor) if service else {'available':False,'plans':[],'reason':'会员购买尚未开放；注册不会自动开通会员'}
        if method=='GET' and path=='/v1/billing/orders':
            return {'available':service is not None,'orders':[public_order(row) for row in service.repository.history(actor)] if service else []}
        if service is None:raise Fault(503,'会员购买尚未开放，不会创建支付或开通会员')
        if method=='POST' and path=='/v1/billing/orders':
            if set(data or {})!={'plan_id','version','idempotency_key','terms_digest'}:raise Fault(400,'请确认完整的当前套餐条款')
            return public_order(service.create_order(actor,data['plan_id'],data['version'],data['idempotency_key'],data['terms_digest']))
        parts=path.strip('/').split('/')
        if len(parts)==4 and parts[:3]==['v1','billing','orders'] and method=='GET':
            return public_order(service.repository.order(actor,parts[3]))
        if len(parts)==5 and parts[:3]==['v1','billing','orders'] and method=='POST':
            if data:raise Fault(400,'订单状态仅由服务器核验，不接受客户端付款声明')
            if parts[4]=='checkout':return service.checkout(actor,parts[3])
            if parts[4]=='reconcile':
                result=service.reconcile(actor,parts[3])
                return public_order(service.repository.order(actor,parts[3]))|{'verification_deferred':bool(result.get('verification_deferred'))}
        raise Fault(404,'未知会员订单操作')
    except BillingError as error:
        messages={
            'membership_purchase_not_enabled':'会员购买尚未开放',
            'checkout_creation_unconfirmed_no_automatic_retry':'支付页面是否创建尚未确认，请核验此订单；不会重复创建',
            'payment_not_verified_no_membership_change':'暂时无法核验付款，会员状态未改变；请稍后核验此订单，勿重复付款',
            'idempotency_key_conflict':'此操作已关联另一订单，请读取订单记录',
            'order_not_found':'未找到当前账号的订单',
            'verified_member_required':'登录已失效，请恢复登录后查看订单',
        }
        raise Fault(401 if str(error)=='verified_member_required' else 404 if str(error)=='order_not_found' else 409,messages.get(str(error),'订单操作未确认，请查看当前订单后再继续；不会自动重复支付')) from None
