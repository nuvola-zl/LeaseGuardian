package com.smartlease.controller;

import com.smartlease.common.result.Result;
import com.smartlease.dto.*;
import com.smartlease.entity.Bill;
import com.smartlease.entity.CheckoutCase;
import com.smartlease.entity.DamageItem;
import com.smartlease.service.CheckoutService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/checkout")
@RequiredArgsConstructor
public class CheckoutController {

    private final CheckoutService checkoutService;

    @GetMapping("/cases/current")
    public Result<CheckoutCase> current(@RequestParam Long tenantId) {
        return Result.success(checkoutService.current(tenantId));
    }

    @PostMapping("/cases")
    public Result<CheckoutCase> create(@RequestParam Long tenantId,
                                       @RequestBody CheckoutCaseCreateRequest req) {
        return Result.success(checkoutService.createCase(tenantId, req));
    }

    @PostMapping("/cases/{caseId}/damages")
    public Result<DamageItem> addDamage(@RequestParam Long tenantId,
                                        @PathVariable Long caseId,
                                        @RequestBody DamageItemCreateRequest req) {
        return Result.success(checkoutService.addDamage(tenantId, caseId, req));
    }

    @PostMapping("/cases/{caseId}/settlement")
    public Result<Bill> settlement(@RequestParam Long tenantId,
                                   @PathVariable Long caseId,
                                   @RequestBody SettlementGenerateRequest req) {
        return Result.success(checkoutService.generateSettlement(tenantId, caseId, req));
    }

    @PostMapping("/cases/{caseId}/confirm")
    public Result<CheckoutCase> confirm(@RequestParam Long tenantId,
                                        @PathVariable Long caseId,
                                        @RequestBody CheckoutConfirmRequest req) {
        return Result.success(checkoutService.confirm(tenantId, caseId, req));
    }

    @PostMapping("/cases/{caseId}/cancel")
    public Result<CheckoutCase> cancel(@RequestParam Long tenantId,
                                       @PathVariable Long caseId,
                                       @RequestBody CheckoutCancelRequest req) {
        return Result.success(checkoutService.cancel(tenantId, caseId, req));
    }

    @GetMapping("/cases/{caseId}/settlement-detail")
    public Result<CheckoutSettlementDetail> settlementDetail(@RequestParam Long tenantId,
                                                             @PathVariable Long caseId) {
        return Result.success(checkoutService.settlementDetail(tenantId, caseId));
    }

    @PostMapping("/cases/{caseId}/move-out-date")
    public Result<CheckoutCase> moveOutDate(@RequestParam Long tenantId,
                                            @PathVariable Long caseId,
                                            @RequestBody CheckoutMoveOutDateRequest req) {
        return Result.success(checkoutService.updateMoveOutDate(tenantId, caseId, req));
    }
}