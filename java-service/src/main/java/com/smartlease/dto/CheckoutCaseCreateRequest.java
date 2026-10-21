package com.smartlease.dto;

import java.time.LocalDate;

public record CheckoutCaseCreateRequest(
        String requestId,
        LocalDate moveOutDate
) {}