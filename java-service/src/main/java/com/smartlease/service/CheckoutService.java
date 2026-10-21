package com.smartlease.service;

import com.smartlease.dto.*;
import com.smartlease.entity.Bill;
import com.smartlease.entity.CheckoutCase;
import com.smartlease.entity.DamageItem;

public interface CheckoutService {

    CheckoutCase createCase(Long tenantId, CheckoutCaseCreateRequest req);

    DamageItem addDamage(Long tenantId, Long caseId, DamageItemCreateRequest req);

    Bill generateSettlement(Long tenantId, Long caseId, SettlementGenerateRequest req);

    CheckoutCase confirm(Long tenantId, Long caseId, CheckoutConfirmRequest req);

    CheckoutCase cancel(Long tenantId, Long caseId, CheckoutCancelRequest req);

    CheckoutCase current(Long tenantId);

    CheckoutCase detail(Long tenantId, Long caseId);

    CheckoutSettlementDetail settlementDetail(Long tenantId, Long caseId);

    CheckoutCase updateMoveOutDate(Long tenantId, Long caseId, CheckoutMoveOutDateRequest req);
}