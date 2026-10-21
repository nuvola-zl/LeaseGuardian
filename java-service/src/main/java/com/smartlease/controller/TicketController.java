package com.smartlease.controller;

import com.smartlease.common.result.Result;
import com.smartlease.dto.TicketCreateRequest;
import com.smartlease.dto.TicketStatusUpdateRequest;
import com.smartlease.entity.RepairTicket;
import com.smartlease.service.RepairTicketService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/tickets")
@RequiredArgsConstructor
public class TicketController {

    private final RepairTicketService repairTicketService;

    @PostMapping
    public Result<RepairTicket> create(@RequestBody TicketCreateRequest req) {
        return Result.success(repairTicketService.create(req));
    }

    @GetMapping("/{id}")
    public Result<RepairTicket> detail(@PathVariable Long id) {
        return Result.success(repairTicketService.getById(id));
    }

    @GetMapping
    public Result<List<RepairTicket>> list(
            @RequestParam(value = "tenant_id", required = false) Long tenantId
    ) {
        return Result.success(repairTicketService.list(tenantId));
    }
    @PatchMapping("/{id}/status")
    public Result<RepairTicket> updateStatus(@PathVariable Long id,
                                             @RequestBody TicketStatusUpdateRequest req) {
        return Result.success(repairTicketService.updateStatus(id, req.status()));
    }
}