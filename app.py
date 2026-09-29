import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="إدارة محل الموبايلات", layout="wide", page_icon="📱")

# CSS لتحسين المظهر وتدعم اللغة العربية (RTL)
st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-baseweb="select"] { direction: rtl; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# الاتصال بقاعدة بيانات Supabase
st.sidebar.title("⚙️ إعدادات الاتصال")
supabase_url = st.sidebar.text_input("Supabase URL", value=st.secrets.get("SUPABASE_URL", ""), type="password")
supabase_key = st.sidebar.text_input("Supabase Key", value=st.secrets.get("SUPABASE_KEY", ""), type="password")

if not supabase_url or not supabase_key:
    st.warning("⚠️ يرجى إدخال بيانات الاتصال بـ Supabase في القائمة الجانبية أو في secrets للبدء.")
    st.stop()

@st.cache_resource
def get_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)

supabase = get_supabase_client(supabase_url, supabase_key)

# القائمة الرئيسية
menu = ["📊 اللوحة الرئيسية", "📦 إدارة المنتجات", "👥 إدارة العملاء والمديونيات", "🧾 إنشاء فاتورة جديدة", "📜 سجل الفواتير وتعديلها", "💵 تسديد الدفعات"]
choice = st.sidebar.selectbox("الانتقال إلى:", menu)

# ---------------------------------------------------------
# 1. اللوحة الرئيسية
# ---------------------------------------------------------
if choice == "📊 اللوحة الرئيسية":
    st.title("📊 لوحة التحكم الإحصائية")
    
    # جلب البيانات
    res_prod = supabase.table("products").select("*").execute()
    res_cust = supabase.table("customers").select("*").execute()
    res_inv = supabase.table("invoices").select("*").execute()
    
    prods = res_prod.data if res_prod.data else []
    custs = res_cust.data if res_cust.data else []
    invs = res_inv.data if res_inv.data else []
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي المنتجات بالمخزن", len(prods))
    
    total_debt = sum([c.get("total_debt", 0) for c in custs])
    col2.metric("إجمالي المديونيات على العملاء", f"{total_debt:,.2f} ج.م")
    
    total_sales = sum([i.get("total_amount", 0) for i in invs])
    col3.metric("إجمالي مبيعات الفواتير", f"{total_sales:,.2f} ج.م")
    
    total_paid = sum([i.get("paid_amount", 0) for i in invs])
    col4.metric("إجمالي المبالغ المحصلة", f"{total_paid:,.2f} ج.م")

    st.markdown("---")
    st.subheader("⚠️ نواقص المخزون (أقل من 3 قطع)")
    low_stock = [p for p in prods if p.get("stock_quantity", 0) <= 3]
    if low_stock:
        st.dataframe(pd.DataFrame(low_stock)[["id", "name", "category", "stock_quantity", "selling_price"]], use_container_width=True)
    else:
        st.success("المخزون بفرعك بحالة جيدة جداً!")

# ---------------------------------------------------------
# 2. إدارة المنتجات
# ---------------------------------------------------------
elif choice == "📦 إدارة المنتجات":
    st.title("📦 إدارة قطع الغيار والمنتجات")
    
    tab1, tab2, tab3 = st.tabs(["📋 عرض المخزون", "➕ إضافة منتج جديد", "✏️ تعديل / حذف منتج"])
    
    with tab1:
        res = supabase.table("products").select("*").order("id", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df.columns = ["الرقم", "اسم المنتج", "التصنيف", "سعر الشراء", "سعر البيع", "الكمية المتاحة", "تاريخ الإضافة"]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد منتجات حالياً.")

    with tab2:
        with st.form("add_product_form"):
            name = st.text_input("اسم المنتج (مثال: شاشة آيفون 11 أو بطارية سامسونج A51)")
            category = st.selectbox("التصنيف", ["شاشات", "بطاريات", "شواحن وكوابل", "إكسسوارات", "أجزاء صيانة أخرى"])
            cost_price = st.number_input("سعر التكلفة (الشراء)", min_value=0.0, step=10.0)
            selling_price = st.number_input("سعر البيع للعميل", min_value=0.0, step=10.0)
            stock_quantity = st.number_input("الكمية المتاحة في المحل", min_value=1, step=1)
            
            submit = st.form_submit_button("إضافة المنتج للمخزن")
            if submit:
                if name:
                    supabase.table("products").insert({
                        "name": name,
                        "category": category,
                        "cost_price": cost_price,
                        "selling_price": selling_price,
                        "stock_quantity": stock_quantity
                    }).execute()
                    st.success("تم إضافة المنتج بنجاح!")
                    st.rerun()
                else:
                    st.error("يرجى إدخال اسم المنتج.")

    with tab3:
        res = supabase.table("products").select("*").execute()
        if res.data:
            prod_dict = {f"{p['id']} - {p['name']} (الكمية: {p['stock_quantity']})": p for p in res.data}
            selected_p = st.selectbox("اختر المنتج للتعديل/الحذف", list(prod_dict.keys()))
            p_data = prod_dict[selected_p]
            
            col_edit, col_del = st.columns(2)
            with col_edit:
                with st.form("edit_prod_form"):
                    new_name = st.text_input("اسم المنتج", value=p_data["name"])
                    new_cat = st.selectbox("التصنيف", ["شاشات", "بطاريات", "شواحن وكوابل", "إكسسوارات", "أجزاء صيانة أخرى"], index=["شاشات", "بطاريات", "شواحن وكوابل", "إكسسوارات", "أجزاء صيانة أخرى"].index(p_data["category"]) if p_data["category"] in ["شاشات", "بطاريات", "شواحن وكوابل", "إكسسوارات", "أجزاء صيانة أخرى"] else 0)
                    new_cost = st.number_input("سعر التكلفة", value=float(p_data["cost_price"]))
                    new_sell = st.number_input("سعر البيع", value=float(p_data["selling_price"]))
                    new_stock = st.number_input("الكمية المتاحة", value=int(p_data["stock_quantity"]))
                    
                    if st.form_submit_button("حفظ التعديلات"):
                        supabase.table("products").update({
                            "name": new_name,
                            "category": new_cat,
                            "cost_price": new_cost,
                            "selling_price": new_sell,
                            "stock_quantity": new_stock
                        }).eq("id", p_data["id"]).execute()
                        st.success("تم تحديث بيانات المنتج!")
                        st.rerun()

            with col_del:
                st.warning("⚠️ منطقة الخطر")
                if st.button("حذف هذا المنتج تماماً"):
                    supabase.table("products").delete().eq("id", p_data["id"]).execute()
                    st.success("تم حذف المنتج!")
                    st.rerun()

# ---------------------------------------------------------
# 3. إدارة العملاء والمديونيات
# ---------------------------------------------------------
elif choice == "👥 إدارة العملاء والمديونيات":
    st.title("👥 سجل العملاء وكشف المديونيات")
    
    col_c1, col_c2 = st.columns([2, 1])
    
    with col_c1:
        st.subheader("📋 قائمة العملاء والديون المتبقية")
        res_c = supabase.table("customers").select("*").order("total_debt", desc=True).execute()
        if res_c.data:
            df_c = pd.DataFrame(res_c.data)
            df_c.columns = ["الرقم", "اسم العميل", "رقم الهاتف", "المديونية المتبقية (ج.م)", "تاريخ التسجيل"]
            st.dataframe(df_c, use_container_width=True)
        else:
            st.info("لا يوجد عملاء مسجلين.")

    with col_c2:
        st.subheader("➕ إضافة عميل جديد")
        with st.form("add_cust_form"):
            c_name = st.text_input("اسم العميل")
            c_phone = st.text_input("رقم الهاتف")
            if st.form_submit_button("إضافة العميل"):
                if c_name:
                    supabase.table("customers").insert({"name": c_name, "phone": c_phone, "total_debt": 0.0}).execute()
                    st.success("تم إضافة العميل بنجاح!")
                    st.rerun()

# ---------------------------------------------------------
# 4. إنشاء فاتورة جديدة
# ---------------------------------------------------------
elif choice == "🧾 إنشاء فاتورة جديدة":
    st.title("🧾 إنشاء فاتورة مبيعات / صيانة")
    
    # اختيار العميل
    res_customers = supabase.table("customers").select("*").execute()
    cust_data = res_customers.data if res_customers.data else []
    
    if not cust_data:
        st.error("يرجى إضافة عملاء أولاً من قائمة إدارة العملاء.")
        st.stop()
        
    cust_options = {f"{c['name']} (الهاتف: {c.get('phone', 'بدون')}) - الدين الحالي: {c['total_debt']} ج.م": c for c in cust_data}
    selected_cust_str = st.selectbox("اختر العميل الفاتورة باسمه", list(cust_options.keys()))
    selected_cust = cust_options[selected_cust_str]

    st.markdown("---")
    st.subheader("🛒 اختيار المنتجات")
    
    res_products = supabase.table("products").select("*").gt("stock_quantity", 0).execute()
    prod_data = res_products.data if res_products.data else []
    
    if "cart" not in st.session_state:
        st.session_state.cart = []
        
    if prod_data:
        p_options = {f"{p['name']} - سعر: {p['selling_price']} ج.م (المتاح: {p['stock_quantity']})": p for p in prod_data}
        selected_p_str = st.selectbox("اختر المنتج لإضافته للفاتورة", list(p_options.keys()))
        selected_p = p_options[selected_p_str]
        
        qty = st.number_input("الكمية المطلوب بيعها", min_value=1, max_value=int(selected_p['stock_quantity']), value=1)
        
        if st.button("➕ إضافة للفاتورة"):
            st.session_state.cart.append({
                "product_id": selected_p["id"],
                "name": selected_p["name"],
                "unit_price": float(selected_p["selling_price"]),
                "quantity": int(qty),
                "total": float(selected_p["selling_price"]) * int(qty)
            })
            st.success(f"تم إضافة {selected_p['name']} للسلّة.")

    # عرض السلة
    if st.session_state.cart:
        st.markdown("### 📋 محتويات الفاتورة")
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df[["name", "unit_price", "quantity", "total"]], use_container_width=True)
        
        total_invoice_sum = sum(item["total"] for item in st.session_state.cart)
        st.markdown(f"### 💰 إجمالي الفاتورة: **{total_invoice_sum:,.2f} ج.م**")
        
        col_pay1, col_pay2 = st.columns(2)
        paid_amount = col_pay1.number_input("المبلغ المدفوع كاش الآن", min_value=0.0, max_value=float(total_invoice_sum), value=float(total_invoice_sum))
        remaining = total_invoice_sum - paid_amount
        col_pay2.metric("المبلغ المتبقي (مديونية آجل)", f"{remaining:,.2f} ج.م")
        
        if st.button("✅ حفظ وإتمام الفاتورة"):
            status = "paid" if remaining == 0 else "partial" if paid_amount > 0 else "unpaid"
            
            # 1. إدراج الفاتورة
            inv_res = supabase.table("invoices").insert({
                "customer_id": selected_cust["id"],
                "total_amount": total_invoice_sum,
                "paid_amount": paid_amount,
                "remaining_amount": remaining,
                "status": status
            }).execute()
            
            invoice_id = inv_res.data[0]["id"]
            
            # 2. إدراج عناصر الفاتورة وتحديث المخزون
            for item in st.session_state.cart:
                # تحديث المخزون
                curr_p = supabase.table("products").select("stock_quantity").eq("id", item["product_id"]).execute().data[0]
                new_qty = curr_p["stock_quantity"] - item["quantity"]
                supabase.table("products").update({"stock_quantity": new_qty}).eq("id", item["product_id"]).execute()
            
            # 3. تحديث مديونية العميل
            if remaining > 0:
                new_debt = float(selected_cust["total_debt"]) + remaining
                supabase.table("customers").update({"total_debt": new_debt}).eq("id", selected_cust["id"]).execute()
                
            st.success("تم حفظ الفاتورة وتحديث المخزون والمديونية بنجاح!")
            st.session_state.cart = []
            st.rerun()

# ---------------------------------------------------------
# 5. سجل الفواتير وتعديلها
# ---------------------------------------------------------
elif choice == "📜 سجل الفواتير وتعديلها":
    st.title("📜 سجل الفواتير وتعديلها")
    
    res_inv = supabase.table("invoices").select("*, customers(name)").order("id", desc=True).execute()
    if res_inv.data:
        invoices_list = []
        for i in res_inv.data:
            cust_name = i["customers"]["name"] if i.get("customers") else "غير معروف"
            invoices_list.append({
                "رقم الفاتورة": i["id"],
                "العميل": cust_name,
                "الإجمالي": i["total_amount"],
                "المدفوع": i["paid_amount"],
                "المتبقي": i["remaining_amount"],
                "الحالة": i["status"],
                "التاريخ": i["created_at"]
            })
        st.dataframe(pd.DataFrame(invoices_list), use_container_width=True)
    else:
        st.info("لا توجد فواتير مسجلة.")

# ---------------------------------------------------------
# 6. تسديد الدفعات
# ---------------------------------------------------------
elif choice == "💵 تسديد الدفعات":
    st.title("💵 تسديد مديونيات العملاء")
    
    res_debtors = supabase.table("customers").select("*").gt("total_debt", 0).execute()
    debtors = res_debtors.data if res_debtors.data else []
    
    if debtors:
        debtor_dict = {f"{c['name']} - المديونية الحالية: {c['total_debt']} ج.م": c for c in debtors}
        selected_d = st.selectbox("اختر العميل لتسجيل دفعة مسددة", list(debtor_dict.keys()))
        customer = debtor_dict[selected_d]
        
        with st.form("pay_debt_form"):
            payment_amount = st.number_input("المبلغ المدفوع حالياً (ج.م)", min_value=1.0, max_value=float(customer["total_debt"]))
            notes = st.text_input("ملاحظات السداد (مثال: دفعة من حساب شاشة آيفون)")
            
            if st.form_submit_button("تسجيل السداد والخصم من المديونية"):
                # 1. إدراج حركة السداد
                supabase.table("payments").insert({
                    "customer_id": customer["id"],
                    "amount_paid": payment_amount,
                    "notes": notes
                }).execute()
                
                # 2. تحديث مديونية العميل
                updated_debt = float(customer["total_debt"]) - payment_amount
                supabase.table("customers").update({"total_debt": updated_debt}).eq("id", customer["id"]).execute()
                
                st.success(f"تم خصم {payment_amount} ج.م بنجاح! المديونية المتبقية على العميل: {updated_debt} ج.م")
                st.rerun()
    else:
        st.success("🎉 لا يوجد أي عملاء عليهم مديونيات حالياً!")