package com.smartlease.dto;

import java.time.LocalDate;

public record CheckoutMoveOutDateRequest(
        String requestId,
        LocalDate moveOutDate
) {}