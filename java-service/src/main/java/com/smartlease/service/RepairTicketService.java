package com.smartlease.service;

import com.smartlease.dto.TicketCreateRequest;
import com.smartlease.entity.RepairTicket;

import java.util.List;

public interface RepairTicketService {

    RepairTicket create(TicketCreateRequest req);

    RepairTicket getById(Long id);

    List<RepairTicket> list(Long tenantId);

    RepairTicket updateStatus(Long id, String status);
}