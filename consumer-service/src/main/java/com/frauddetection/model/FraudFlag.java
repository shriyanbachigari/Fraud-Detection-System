package com.frauddetection.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "flags")
public class FraudFlag {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false)
    private String txnId;
    
    private Double score;
    
    private Boolean labelPred;
    
    @Column(columnDefinition = "TEXT")
    private String reasonsJson;
    
    @Column(nullable = false)
    private Instant timestamp;

    public FraudFlag() {
        this.timestamp = Instant.now();
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getTxnId() { return txnId; }
    public void setTxnId(String txnId) { this.txnId = txnId; }
    
    public Double getScore() { return score; }
    public void setScore(Double score) { this.score = score; }
    
    public Boolean getLabelPred() { return labelPred; }
    public void setLabelPred(Boolean labelPred) { this.labelPred = labelPred; }
    
    public String getReasonsJson() { return reasonsJson; }
    public void setReasonsJson(String reasonsJson) { this.reasonsJson = reasonsJson; }
    
    public Instant getTimestamp() { return timestamp; }
    public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }
}
