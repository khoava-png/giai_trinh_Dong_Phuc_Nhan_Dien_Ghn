# DATA MODEL TRUTH — ORDER-ROOT-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-002  

## 1. Phân loại Mô hình Dữ liệu từng Tab (Data Model Truth)

| Tab Name | Phân loại Mô hình (Data Model Type) | Owner | Writer | Readers | Update Frequency | Expected Lifetime | Old Rows Remain? | Manual Editing? |
|---|---|---|---|---|---|---|---|---|
| **Chi_tiet** | **CURRENT_STATE_SNAPSHOT** | Python Backend | Python Backend (`cao_ton_phieu.py`) | Backend / Dashboard | Mỗi chu kỳ cào | Vòng đời chu kỳ | Không (Full replace) | Không nên |
| **Ton_phieu** | **CURRENT_STATE_SNAPSHOT** | Python Backend | Python Backend (`cao_ton_phieu.py`) | Backend / Dashboard | Mỗi chu kỳ cào | Vòng đời chu kỳ | Không (Full replace) | Không nên |
| **RP_theo_AM** | **DERIVED_REPORT** | Python Backend | Python Backend (`cao_ton_phieu.py`) | Backend / GTalk | Mỗi chu kỳ cào | Vòng đời chu kỳ | Không (Full replace) | Không nên |
| **RP_theo_TroLy** | **DERIVED_REPORT** | Python Backend | Python Backend (`cao_ton_phieu.py`) | Backend / GTalk | Mỗi chu kỳ cào | Vòng đời chu kỳ | Không (Full replace) | Không nên |
| **Co_Cau** | **MASTER_DATA** | Admin / Setup | Manual / Admin | Python Backend | Khi thay đổi cơ cấu | Dài hạn | Có | Có |
