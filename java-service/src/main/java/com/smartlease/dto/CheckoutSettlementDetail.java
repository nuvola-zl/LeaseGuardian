package com.smartlease.dto;

import com.smartlease.entity.Bill;
import com.smartlease.entity.BillItem;
import com.smartlease.entity.CheckoutCase;
import com.smartlease.entity.DamageItem;

import java.util.List;

public record CheckoutSettlementDetail(
        CheckoutCase checkoutCase,
        Bill bill,
        List<BillItem> billItems,
        List<DamageItem> damageItems
) {}