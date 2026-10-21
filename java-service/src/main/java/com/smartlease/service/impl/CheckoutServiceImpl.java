package com.smartlease.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.smartlease.common.code.ErrorCode;
import com.smartlease.common.exception.BusinessException;
import com.smartlease.dto.*;
import com.smartlease.entity.Bill;
import com.smartlease.entity.BillItem;
import com.smartlease.entity.CheckoutCase;
import com.smartlease.entity.DamageItem;
import com.smartlease.entity.Lease;
import com.smartlease.enums.BillDirection;
import com.smartlease.enums.BillItemCode;
import com.smartlease.enums.BillStatus;
import com.smartlease.enums.BillType;
import com.smartlease.enums.CheckoutCaseStatus;
import com.smartlease.enums.DamageResponsibility;
import com.smartlease.enums.DamageReviewStatus;
import com.smartlease.mapper.BillItemMapper;
import com.smartlease.mapper.BillMapper;
import com.smartlease.mapper.CheckoutCaseMapper;
import com.smartlease.mapper.DamageItemMapper;
import com.smartlease.mapper.LeaseMapper;
import com.smartlease.service.CheckoutService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;

@Service
@RequiredArgsConstructor
public class CheckoutServiceImpl implements CheckoutService {

    private final CheckoutCaseMapper checkoutCaseMapper;
    private final DamageItemMapper damageItemMapper;
    private final BillMapper billMapper;
    private final BillItemMapper billItemMapper;
    private final LeaseMapper leaseMapper;

    private static final String LEASE_ACTIVE = "ACTIVE";
    private static final String LEASE_TERMINATING = "TERMINATING";
    private static final String LEASE_TERMINATED = "TERMINATED";

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CheckoutCase createCase(Long tenantId, CheckoutCaseCreateRequest req) {
        requireTenant(tenantId);

        String requestId = (req != null && StringUtils.hasText(req.requestId()))
                ? req.requestId()
                : java.util.UUID.randomUUID().toString().replace("-", "");

        if (req != null && StringUtils.hasText(req.requestId())) {
            CheckoutCase existed = checkoutCaseMapper.selectOne(
                    Wrappers.<CheckoutCase>lambdaQuery().eq(CheckoutCase::getRequestId, req.requestId())
            );
            if (existed != null) {
                if (!existed.getTenantId().equals(tenantId)) {
                    throw BusinessException.conflict(ErrorCode.RESOURCE_DUPLICATE, "requestId belongs to another tenant");
                }
                return existed;
            }
        }

        Lease lease = activeLeaseOf(tenantId);
        if (req != null && req.moveOutDate() != null) {
            validateMoveOutDate(req.moveOutDate(), lease);
        }

        LocalDateTime now = LocalDateTime.now();

        CheckoutCase c = new CheckoutCase();
        c.setTenantId(tenantId);
        c.setLeaseId(lease.getId());
        c.setRequestId(requestId);
        c.setStatus(CheckoutCaseStatus.APPLYING.name());
        c.setMoveOutDate(req != null ? req.moveOutDate() : null);
        c.setSettlementVersion(0);
        c.setHasPendingDamage(false);
        c.setVersion(0);
        c.setCreatedAt(now);
        c.setUpdatedAt(now);
        checkoutCaseMapper.insert(c);

        int rows = leaseMapper.update(null, Wrappers.<Lease>lambdaUpdate()
                .eq(Lease::getId, lease.getId())
                .eq(Lease::getStatus, LEASE_ACTIVE)
                .set(Lease::getStatus, LEASE_TERMINATING)
                .set(req != null && req.moveOutDate() != null, Lease::getMoveOutDate, req.moveOutDate())
                .set(Lease::getUpdatedAt, now)
        );
        if (rows == 0) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "lease status changed concurrently");
        }

        return checkoutCaseMapper.selectById(c.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public DamageItem addDamage(Long tenantId, Long caseId, DamageItemCreateRequest req) {
        CheckoutCase c = ownedActiveCase(tenantId, caseId);

        if (req == null
                || !StringUtils.hasText(req.itemName())
                || !StringUtils.hasText(req.responsibility())) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "itemName/responsibility is required");
        }

        DamageResponsibility responsibility;
        try {
            responsibility = DamageResponsibility.valueOf(req.responsibility());
        } catch (IllegalArgumentException e) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "unknown responsibility: " + req.responsibility());
        }

        if (responsibility == DamageResponsibility.TENANT) {
            requireBasis(req.basisDocId(), req.basisClauseNo(), req.basisExcerpt());
            if (req.referenceAmount() == null || req.referenceAmount().compareTo(BigDecimal.ZERO) < 0) {
                throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "valid referenceAmount is required for TENANT damage");
            }
        }

        if (StringUtils.hasText(req.requestId())) {
            DamageItem existed = damageItemMapper.selectOne(
                    Wrappers.<DamageItem>lambdaQuery().eq(DamageItem::getRequestId, req.requestId())
            );
            if (existed != null) {
                if (!existed.getTenantId().equals(tenantId) || !existed.getCaseId().equals(caseId)) {
                    throw BusinessException.conflict(ErrorCode.RESOURCE_DUPLICATE, "requestId belongs to another damage item");
                }
                return existed;
            }
        }

        LocalDateTime now = LocalDateTime.now();

        DamageItem item = new DamageItem();
        item.setCaseId(c.getId());
        item.setTenantId(tenantId);
        item.setItemName(req.itemName());
        item.setDescription(req.description());
        item.setResponsibility(responsibility.name());
        item.setReferenceAmount(req.referenceAmount());
        item.setBasisDocId(req.basisDocId());
        item.setBasisClauseNo(req.basisClauseNo());
        item.setBasisExcerpt(req.basisExcerpt());
        item.setRequestId(StringUtils.hasText(req.requestId()) ? req.requestId() : null);
        item.setCreatedAt(now);
        item.setUpdatedAt(now);

        if (responsibility == DamageResponsibility.TENANT) {
            item.setReviewStatus(DamageReviewStatus.RESOLVED.name());
            item.setFinalAmount(req.referenceAmount());
        } else if (responsibility == DamageResponsibility.MANUAL_PENDING) {
            item.setReviewStatus(DamageReviewStatus.PENDING.name());
            item.setFinalAmount(null);
        } else {
            item.setReviewStatus(DamageReviewStatus.NOT_REQUIRED.name());
            item.setFinalAmount(null);
        }

        damageItemMapper.insert(item);
        refreshPendingDamageFlag(c.getId());
        return damageItemMapper.selectById(item.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Bill generateSettlement(Long tenantId, Long caseId, SettlementGenerateRequest req) {
        CheckoutCase c = ownedActiveCase(tenantId, caseId);

        if (!CheckoutCaseStatus.APPLYING.name().equals(c.getStatus())
                && !CheckoutCaseStatus.AWAITING_CONFIRM.name().equals(c.getStatus())) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "case is not active");
        }
        if (req == null || !StringUtils.hasText(req.requestId())) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "requestId is required");
        }
        if (c.getMoveOutDate() == null) {
            throw BusinessException.badRequest(ErrorCode.CHECKOUT_MOVE_OUT_DATE_INVALID, "moveOutDate is required");
        }

        Lease lease = leaseMapper.selectById(c.getLeaseId());
        if (lease == null || !lease.getTenantId().equals(tenantId)) {
            throw BusinessException.notFound(ErrorCode.LEASE_NOT_FOUND, "lease not found");
        }
        validateMoveOutDate(c.getMoveOutDate(), lease);

        List<DamageItem> damages = damageItemMapper.selectList(
                Wrappers.<DamageItem>lambdaQuery().eq(DamageItem::getCaseId, c.getId())
        );

        boolean hasPending = damages.stream().anyMatch(d ->
                DamageResponsibility.MANUAL_PENDING.name().equals(d.getResponsibility())
                        || (DamageResponsibility.TENANT.name().equals(d.getResponsibility())
                        && (!DamageReviewStatus.RESOLVED.name().equals(d.getReviewStatus())
                        || d.getFinalAmount() == null))
        );

        BigDecimal damageTotal = damages.stream()
                .filter(d -> DamageResponsibility.TENANT.name().equals(d.getResponsibility()))
                .filter(d -> DamageReviewStatus.RESOLVED.name().equals(d.getReviewStatus()))
                .map(DamageItem::getFinalAmount)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        List<Bill> utilityBills = billMapper.selectList(
                Wrappers.<Bill>lambdaQuery()
                        .eq(Bill::getTenantId, tenantId)
                        .eq(Bill::getLeaseId, c.getLeaseId())
                        .eq(Bill::getBillType, BillType.UTILITY_DEBT.name())
                        .eq(Bill::getStatus, BillStatus.OPEN.name())
        );
        BigDecimal utilityDebt = utilityBills.stream()
                .map(Bill::getAmount)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        int months = unusedWholeMonths(c.getMoveOutDate(), lease.getEndDate());
        BigDecimal unusedRent = lease.getMonthlyRent().multiply(BigDecimal.valueOf(months));
        BigDecimal expectedRefund = lease.getDeposit()
                .add(unusedRent)
                .subtract(utilityDebt)
                .subtract(damageTotal);

        LocalDateTime now = LocalDateTime.now();

        if (c.getSettlementBillId() != null) {
            billMapper.update(null, Wrappers.<Bill>lambdaUpdate()
                    .eq(Bill::getId, c.getSettlementBillId())
                    .eq(Bill::getStatus, BillStatus.OPEN.name())
                    .set(Bill::getStatus, BillStatus.CANCELLED.name())
                    .set(Bill::getUpdatedAt, now)
            );
        }

        Bill bill = new Bill();
        bill.setTenantId(tenantId);
        bill.setLeaseId(c.getLeaseId());
        bill.setCaseId(c.getId());
        bill.setRequestId(req.requestId());
        bill.setBillType(BillType.SETTLEMENT_REFUND.name());
        bill.setDirection(BillDirection.REFUND.name());
        bill.setAmount(expectedRefund);
        bill.setStatus(BillStatus.OPEN.name());
        bill.setSource("SYSTEM");
        bill.setGeneratedAt(now);
        bill.setCreatedAt(now);
        bill.setUpdatedAt(now);
        billMapper.insert(bill);

        int lineNo = 1;
        insertBillItem(bill.getId(), lineNo++, BillItemCode.DEPOSIT_REFUND, "押金退还",
                BillDirection.REFUND, lease.getDeposit(), null, null,
                "deposit_snapshot", "LEASE", "DEPOSIT", "押金按合同退还");

        insertBillItem(bill.getId(), lineNo++, BillItemCode.UNUSED_RENT, "剩余整月租金",
                BillDirection.REFUND, unusedRent, months, lease.getMonthlyRent(),
                "max(0,(endYm-moveYm)-1)*monthlyRent",
                "LEASE", "UNUSED_RENT", "剩余整自然月租金退还");

        if (utilityDebt.compareTo(BigDecimal.ZERO) > 0) {
            insertBillItem(bill.getId(), lineNo++, BillItemCode.UTILITY_DEBT, "水电欠费扣减",
                    BillDirection.RECEIVABLE, utilityDebt, null, null,
                    "sum(open utility bills)",
                    "BILL", "OPEN_UTILITY", "未结清水电账单扣减");
        }

        if (damageTotal.compareTo(BigDecimal.ZERO) > 0) {
            String[] basis = firstResolvedDamageBasis(damages);
            insertBillItem(bill.getId(), lineNo, BillItemCode.DAMAGE_COMPENSATION, "损坏赔偿扣减",
                    BillDirection.RECEIVABLE, damageTotal, null, null,
                    "sum(resolved tenant damage final_amount)",
                    basis[0], basis[1], basis[2]);
        }

        int rows = checkoutCaseMapper.update(null, Wrappers.<CheckoutCase>lambdaUpdate()
                .eq(CheckoutCase::getId, c.getId())
                .eq(CheckoutCase::getVersion, c.getVersion())
                .set(CheckoutCase::getStatus, CheckoutCaseStatus.AWAITING_CONFIRM.name())
                .set(CheckoutCase::getSettlementBillId, bill.getId())
                .set(CheckoutCase::getSettlementVersion, c.getSettlementVersion() + 1)
                .set(CheckoutCase::getExpectedRefundAmount, expectedRefund)
                .set(CheckoutCase::getHasPendingDamage, hasPending)
                .set(CheckoutCase::getVersion, c.getVersion() + 1)
                .set(CheckoutCase::getUpdatedAt, now)
        );
        if (rows == 0) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "case changed concurrently");
        }

        return billMapper.selectById(bill.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CheckoutCase confirm(Long tenantId, Long caseId, CheckoutConfirmRequest req) {
        CheckoutCase c = ownedActiveCase(tenantId, caseId);

        if (!CheckoutCaseStatus.AWAITING_CONFIRM.name().equals(c.getStatus())) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "case is not awaiting confirm");
        }
        if (Boolean.TRUE.equals(c.getHasPendingDamage())) {
            throw BusinessException.conflict(ErrorCode.CHECKOUT_PENDING_DAMAGE, "damage item is pending manual review");
        }
        if (req == null
                || req.settlementVersion() == null
                || !req.settlementVersion().equals(c.getSettlementVersion())) {
            throw BusinessException.conflict(ErrorCode.CHECKOUT_SETTLEMENT_VERSION_MISMATCH, "settlement version mismatch");
        }

        Bill bill = c.getSettlementBillId() == null ? null : billMapper.selectById(c.getSettlementBillId());
        if (bill == null || !BillStatus.OPEN.name().equals(bill.getStatus())) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "settlement bill is not open");
        }

        LocalDateTime now = LocalDateTime.now();

        int caseRows = checkoutCaseMapper.update(null, Wrappers.<CheckoutCase>lambdaUpdate()
                .eq(CheckoutCase::getId, c.getId())
                .eq(CheckoutCase::getVersion, c.getVersion())
                .set(CheckoutCase::getStatus, CheckoutCaseStatus.COMPLETED.name())
                .set(CheckoutCase::getCompletedAt, now)
                .set(CheckoutCase::getVersion, c.getVersion() + 1)
                .set(CheckoutCase::getUpdatedAt, now)
        );
        if (caseRows == 0) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "case changed concurrently");
        }

        int leaseRows = leaseMapper.update(null, Wrappers.<Lease>lambdaUpdate()
                .eq(Lease::getId, c.getLeaseId())
                .eq(Lease::getStatus, LEASE_TERMINATING)
                .set(Lease::getStatus, LEASE_TERMINATED)
                .set(Lease::getMoveOutDate, c.getMoveOutDate())
                .set(Lease::getTerminatedAt, now)
                .set(Lease::getUpdatedAt, now)
        );
        if (leaseRows == 0) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "lease status changed concurrently");
        }

        billMapper.update(null, Wrappers.<Bill>lambdaUpdate()
                .eq(Bill::getId, bill.getId())
                .eq(Bill::getStatus, BillStatus.OPEN.name())
                .set(Bill::getStatus, BillStatus.CLOSED.name())
                .set(Bill::getUpdatedAt, now)
        );

        billMapper.update(null, Wrappers.<Bill>lambdaUpdate()
                .eq(Bill::getTenantId, tenantId)
                .eq(Bill::getLeaseId, c.getLeaseId())
                .eq(Bill::getBillType, BillType.UTILITY_DEBT.name())
                .eq(Bill::getStatus, BillStatus.OPEN.name())
                .set(Bill::getStatus, BillStatus.CLOSED.name())
                .set(Bill::getUpdatedAt, now)
        );

        return checkoutCaseMapper.selectById(c.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CheckoutCase cancel(Long tenantId, Long caseId, CheckoutCancelRequest req) {
        CheckoutCase c = ownedActiveCase(tenantId, caseId);

        LocalDateTime now = LocalDateTime.now();

        int caseRows = checkoutCaseMapper.update(null, Wrappers.<CheckoutCase>lambdaUpdate()
                .eq(CheckoutCase::getId, c.getId())
                .eq(CheckoutCase::getVersion, c.getVersion())
                .set(CheckoutCase::getStatus, CheckoutCaseStatus.CANCELLED.name())
                .set(CheckoutCase::getCancelledAt, now)
                .set(CheckoutCase::getVersion, c.getVersion() + 1)
                .set(CheckoutCase::getUpdatedAt, now)
        );
        if (caseRows == 0) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "case changed concurrently");
        }

        int leaseRows = leaseMapper.update(null, Wrappers.<Lease>lambdaUpdate()
                .eq(Lease::getId, c.getLeaseId())
                .eq(Lease::getStatus, LEASE_TERMINATING)
                .set(Lease::getStatus, LEASE_ACTIVE)
                .set(Lease::getMoveOutDate, null)
                .set(Lease::getUpdatedAt, now)
        );
        if (leaseRows == 0) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "lease status changed concurrently");
        }

        if (c.getSettlementBillId() != null) {
            billMapper.update(null, Wrappers.<Bill>lambdaUpdate()
                    .eq(Bill::getId, c.getSettlementBillId())
                    .eq(Bill::getStatus, BillStatus.OPEN.name())
                    .set(Bill::getStatus, BillStatus.CANCELLED.name())
                    .set(Bill::getUpdatedAt, now)
            );
        }

        return checkoutCaseMapper.selectById(c.getId());
    }

    @Override
    public CheckoutCase current(Long tenantId) {
        requireTenant(tenantId);
        return checkoutCaseMapper.selectOne(
                Wrappers.<CheckoutCase>lambdaQuery()
                        .eq(CheckoutCase::getTenantId, tenantId)
                        .in(CheckoutCase::getStatus,
                                CheckoutCaseStatus.APPLYING.name(),
                                CheckoutCaseStatus.AWAITING_CONFIRM.name())
                        .orderByDesc(CheckoutCase::getId)
                        .last("limit 1")
        );
    }

    @Override
    public CheckoutCase detail(Long tenantId, Long caseId) {
        requireTenant(tenantId);
        if (caseId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "caseId is required");
        }
        CheckoutCase c = checkoutCaseMapper.selectById(caseId);
        if (c == null || !c.getTenantId().equals(tenantId)) {
            throw BusinessException.notFound(ErrorCode.RESOURCE_NOT_FOUND, "checkout case not found");
        }
        return c;
    }

    private void requireTenant(Long tenantId) {
        if (tenantId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "tenantId is required");
        }
    }

    private Lease activeLeaseOf(Long tenantId) {
        Lease lease = leaseMapper.selectOne(
                Wrappers.<Lease>lambdaQuery()
                        .eq(Lease::getTenantId, tenantId)
                        .in(Lease::getStatus, LEASE_ACTIVE, LEASE_TERMINATING)
                        .orderByDesc(Lease::getId)
                        .last("limit 1")
        );
        if (lease == null) {
            throw BusinessException.notFound(ErrorCode.LEASE_NOT_FOUND, "active lease not found or expired");
        }
        if (LEASE_TERMINATING.equals(lease.getStatus())) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "lease already terminating");
        }
        return lease;
    }

    private CheckoutCase ownedActiveCase(Long tenantId, Long caseId) {
        requireTenant(tenantId);
        if (caseId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "caseId is required");
        }
        CheckoutCase c = checkoutCaseMapper.selectById(caseId);
        if (c == null || !c.getTenantId().equals(tenantId)) {
            throw BusinessException.notFound(ErrorCode.RESOURCE_NOT_FOUND, "checkout case not found");
        }
        final CheckoutCaseStatus status;
        try {
            status = CheckoutCaseStatus.valueOf(c.getStatus());
        } catch (IllegalArgumentException e) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "unknown case status: " + c.getStatus());
        }
        if (!status.active()) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "case already ended");
        }
        return c;
    }

    private void validateMoveOutDate(LocalDate moveOutDate, Lease lease) {
        if (moveOutDate.isAfter(lease.getEndDate())) {
            throw BusinessException.badRequest(
                    ErrorCode.CHECKOUT_MOVE_OUT_DATE_INVALID,
                    "moveOutDate must be before or equal to lease.endDate"
            );
        }
    }

    private int unusedWholeMonths(LocalDate moveOutDate, LocalDate endDate) {
        int diff = (endDate.getYear() * 12 + endDate.getMonthValue())
                - (moveOutDate.getYear() * 12 + moveOutDate.getMonthValue())
                - 1;
        return Math.max(diff, 0);
    }

    private void refreshPendingDamageFlag(Long caseId) {
        Long pending = damageItemMapper.selectCount(
                Wrappers.<DamageItem>lambdaQuery()
                        .eq(DamageItem::getCaseId, caseId)
                        .and(w -> w.eq(DamageItem::getResponsibility, DamageResponsibility.MANUAL_PENDING.name())
                                .or(x -> x.eq(DamageItem::getResponsibility, DamageResponsibility.TENANT.name())
                                        .and(y -> y.ne(DamageItem::getReviewStatus, DamageReviewStatus.RESOLVED.name())
                                                .or()
                                                .isNull(DamageItem::getFinalAmount))))
        );


        checkoutCaseMapper.update(null, Wrappers.<CheckoutCase>lambdaUpdate()
                .eq(CheckoutCase::getId, caseId)
                .set(CheckoutCase::getHasPendingDamage, pending != null && pending > 0)
                .set(CheckoutCase::getUpdatedAt, LocalDateTime.now())
        );
    }

    private void insertBillItem(Long billId,
                                int lineNo,
                                BillItemCode code,
                                String name,
                                BillDirection direction,
                                BigDecimal amount,
                                Integer months,
                                BigDecimal monthlyRent,
                                String formula,
                                String basisDoc,
                                String basisClause,
                                String basisExcerpt) {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) < 0) {
            throw BusinessException.badRequest(ErrorCode.CHECKOUT_BILL_BASIS_MISSING, "bill item amount invalid");
        }
        requireBasis(basisDoc, basisClause, basisExcerpt);

        BillItem item = new BillItem();
        item.setBillId(billId);
        item.setLineNo(lineNo);
        item.setItemCode(code.name());
        item.setItemName(name);
        item.setDirection(direction.name());
        item.setAmount(amount);
        item.setMonths(months);
        item.setMonthlyRent(monthlyRent);
        item.setFormulaSnapshot(formula);
        item.setBasisDocId(basisDoc);
        item.setBasisClauseNo(basisClause);
        item.setBasisExcerpt(basisExcerpt);
        item.setCreatedAt(LocalDateTime.now());
        billItemMapper.insert(item);
    }

    private String[] firstResolvedDamageBasis(List<DamageItem> damages) {
        return damages.stream()
                .filter(d -> DamageResponsibility.TENANT.name().equals(d.getResponsibility()))
                .filter(d -> DamageReviewStatus.RESOLVED.name().equals(d.getReviewStatus()))
                .filter(d -> d.getFinalAmount() != null)
                .findFirst()
                .map(d -> new String[]{d.getBasisDocId(), d.getBasisClauseNo(), d.getBasisExcerpt()})
                .orElseThrow(() -> BusinessException.badRequest(
                        ErrorCode.CHECKOUT_BILL_BASIS_MISSING,
                        "resolved tenant damage basis is required"
                ));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CheckoutCase updateMoveOutDate(Long tenantId, Long caseId, CheckoutMoveOutDateRequest req) {
        CheckoutCase c = ownedActiveCase(tenantId, caseId);

        if (req == null || req.moveOutDate() == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "moveOutDate is required");
        }

        Lease lease = leaseMapper.selectById(c.getLeaseId());
        if (lease == null || !lease.getTenantId().equals(tenantId)) {
            throw BusinessException.notFound(ErrorCode.LEASE_NOT_FOUND, "lease not found");
        }
        validateMoveOutDate(req.moveOutDate(), lease);

        LocalDateTime now = LocalDateTime.now();

        int caseRows = checkoutCaseMapper.update(null, Wrappers.<CheckoutCase>lambdaUpdate()
                .eq(CheckoutCase::getId, c.getId())
                .eq(CheckoutCase::getVersion, c.getVersion())
                .set(CheckoutCase::getMoveOutDate, req.moveOutDate())
                .set(CheckoutCase::getVersion, c.getVersion() + 1)
                .set(CheckoutCase::getUpdatedAt, now)
        );
        if (caseRows == 0) {
            throw BusinessException.conflict(ErrorCode.LEASE_STATUS_INVALID, "case changed concurrently");
        }

        leaseMapper.update(null, Wrappers.<Lease>lambdaUpdate()
                .eq(Lease::getId, c.getLeaseId())
                .eq(Lease::getStatus, LEASE_TERMINATING)
                .set(Lease::getMoveOutDate, req.moveOutDate())
                .set(Lease::getUpdatedAt, now)
        );

        return checkoutCaseMapper.selectById(c.getId());
    }

    @Override
    public CheckoutSettlementDetail settlementDetail(Long tenantId, Long caseId) {
        requireTenant(tenantId);
        if (caseId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "caseId is required");
        }

        CheckoutCase c = checkoutCaseMapper.selectById(caseId);
        if (c == null || !c.getTenantId().equals(tenantId)) {
            throw BusinessException.notFound(ErrorCode.RESOURCE_NOT_FOUND, "checkout case not found");
        }

        Bill bill = null;
        List<BillItem> billItems = List.of();

        if (c.getSettlementBillId() != null) {
            bill = billMapper.selectById(c.getSettlementBillId());
            if (bill == null
                    || !bill.getTenantId().equals(tenantId)
                    || !bill.getCaseId().equals(c.getId())) {
                throw BusinessException.notFound(ErrorCode.RESOURCE_NOT_FOUND, "settlement bill not found");
            }

            billItems = billItemMapper.selectList(
                    Wrappers.<BillItem>lambdaQuery()
                            .eq(BillItem::getBillId, bill.getId())
                            .orderByAsc(BillItem::getLineNo)
            );
        }

        List<DamageItem> damageItems = damageItemMapper.selectList(
                Wrappers.<DamageItem>lambdaQuery()
                        .eq(DamageItem::getCaseId, c.getId())
                        .orderByAsc(DamageItem::getId)
        );

        return new CheckoutSettlementDetail(c, bill, billItems, damageItems);
    }

    private void requireBasis(String basisDocId, String basisClauseNo, String basisExcerpt) {
        if (!StringUtils.hasText(basisDocId)
                || !StringUtils.hasText(basisClauseNo)
                || !StringUtils.hasText(basisExcerpt)) {
            throw BusinessException.badRequest(ErrorCode.CHECKOUT_BILL_BASIS_MISSING, "basis is required");
        }
    }
}