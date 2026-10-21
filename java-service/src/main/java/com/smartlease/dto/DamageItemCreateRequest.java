package com.smartlease.dto;

import java.math.BigDecimal;

public record DamageItemCreateRequest(
        String requestId,
        String itemName,
        String description,
        String responsibility,
        BigDecimal referenceAmount,
        String basisDocId,
        String basisClauseNo,
        String basisExcerpt
) {}