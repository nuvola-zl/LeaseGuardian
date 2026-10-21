package com.smartlease.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.smartlease.common.code.ErrorCode;
import com.smartlease.common.exception.BusinessException;
import com.smartlease.dto.TicketCreateRequest;
import com.smartlease.entity.RepairTicket;
import com.smartlease.enums.RepairTicketStatus;
import com.smartlease.mapper.RepairTicketMapper;
import com.smartlease.service.RepairTicketService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.List;

@Service
@RequiredArgsConstructor
public class RepairTicketServiceImpl implements RepairTicketService {

    private final RepairTicketMapper repairTicketMapper;

    @Override
    public RepairTicket create(TicketCreateRequest req) {
        if (req == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "request body is required");
        }
        if (req.tenantId() == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "tenant_id is required");
        }
        if (!StringUtils.hasText(req.description())) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "description is required");
        }

        if (StringUtils.hasText(req.requestId())) {
            Long count = repairTicketMapper.selectCount(
                    Wrappers.<RepairTicket>lambdaQuery()
                            .eq(RepairTicket::getRequestId, req.requestId())
            );
            if (count != null && count > 0) {
                throw BusinessException.conflict(
                        ErrorCode.TICKET_DUPLICATE,
                        "duplicate request_id: " + req.requestId()
                );
            }
        }

        RepairTicket ticket = new RepairTicket();
        ticket.setTenantId(req.tenantId());
        ticket.setDescription(req.description());
        ticket.setStatus(RepairTicketStatus.REGISTERED.name());
        ticket.setRequestId(StringUtils.hasText(req.requestId()) ? req.requestId() : null);

        repairTicketMapper.insert(ticket);
        return getById(ticket.getId());
    }

    @Override
    public RepairTicket getById(Long id) {
        if (id == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "id is required");
        }
        RepairTicket ticket = repairTicketMapper.selectById(id);
        if (ticket == null) {
            throw BusinessException.notFound(
                    ErrorCode.TICKET_NOT_FOUND,
                    "ticket not found: " + id
            );
        }
        return ticket;
    }

    @Override
    public List<RepairTicket> list(Long tenantId) {
        var wrapper = Wrappers.<RepairTicket>lambdaQuery()
                .orderByDesc(RepairTicket::getCreatedAt);
        if (tenantId != null) {
            wrapper.eq(RepairTicket::getTenantId, tenantId);
        }
        return repairTicketMapper.selectList(wrapper);
    }

    @Override
    public RepairTicket updateStatus(Long id, String status) {
        RepairTicket ticket = getById(id);

        if (!StringUtils.hasText(status)) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "status is required");
        }

        RepairTicketStatus from;
        RepairTicketStatus to;
        try {
            from = RepairTicketStatus.valueOf(ticket.getStatus());
            to = RepairTicketStatus.valueOf(status);
        } catch (IllegalArgumentException ex) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "unknown status: " + status);
        }

        if (!from.canTransitionTo(to)) {
            throw BusinessException.conflict(
                    ErrorCode.TICKET_STATUS_INVALID,
                    "invalid status transition: " + from + " -> " + to
            );
        }

        RepairTicket update = new RepairTicket();
        update.setId(id);
        update.setStatus(to.name());
        repairTicketMapper.updateById(update);

        return getById(id);
    }
}