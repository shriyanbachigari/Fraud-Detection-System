package com.frauddetection.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.frauddetection.model.FraudFlag;
import com.frauddetection.model.Transaction;
import com.frauddetection.repository.FraudFlagRepository;
import com.frauddetection.repository.TransactionRepository;
import com.frauddetection.service.ModelClient;
import com.frauddetection.service.VelocityService;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;

@Component
public class TransactionConsumer {
    
    private final VelocityService velocityService;
    private final ModelClient modelClient;
    private final TransactionRepository transactionRepo;
    private final FraudFlagRepository fraudFlagRepo;
    private final ObjectMapper objectMapper;
    
    public TransactionConsumer(
        VelocityService velocityService,
        ModelClient modelClient,
        TransactionRepository transactionRepo,
        FraudFlagRepository fraudFlagRepo
    ) {
        this.velocityService = velocityService;
        this.modelClient = modelClient;
        this.transactionRepo = transactionRepo;
        this.fraudFlagRepo = fraudFlagRepo;
        this.objectMapper = new ObjectMapper();
    }
    
    @KafkaListener(topics = "${kafka.topic.transactions}", groupId = "${spring.kafka.consumer.group-id}")
    public void consume(String message) {
        try {
            JsonNode event = objectMapper.readTree(message);
            
            String txnId = event.get("txn_id").asText();
            
            if (velocityService.isDuplicate(txnId)) {
                return;
            }
            
            String userId = event.get("user_id").asText();
            double amount = event.get("amount").asDouble();
            String country = event.get("country").asText();
            String deviceId = event.get("device_id").asText();
            String timestampStr = event.get("timestamp").asText();
            Instant timestamp = OffsetDateTime.parse(timestampStr).toInstant();
            
            int velocity = velocityService.incrementVelocity(userId);
            boolean isNewCountry = velocityService.isNewCountry(userId, country);
            boolean isNewDevice = velocityService.isNewDevice(userId, deviceId);
            int hour = timestamp.atZone(ZoneOffset.UTC).getHour();
            
            ModelClient.ModelScore modelScore = modelClient.score(
                amount, 
                hour, 
                isNewCountry ? 1 : 0, 
                isNewDevice ? 1 : 0, 
                velocity
            );
            
            boolean isFraud = modelScore.isFraud() 
                || velocity > 8 
                || (isNewCountry && isNewDevice && amount > 500)
                || (isNewCountry && amount > 1000);
            
            Transaction txn = new Transaction();
            txn.setTxnId(txnId);
            txn.setUserId(userId);
            txn.setAmount(BigDecimal.valueOf(amount));
            txn.setCurrency(event.has("currency") ? event.get("currency").asText() : "USD");
            txn.setCountry(country);
            txn.setDeviceId(deviceId);
            txn.setTimestamp(timestamp);
            
            Map<String, Object> features = new HashMap<>();
            features.put("velocity", velocity);
            features.put("new_country", isNewCountry);
            features.put("new_device", isNewDevice);
            features.put("hour", hour);
            txn.setFeaturesJson(objectMapper.writeValueAsString(features));
            
            transactionRepo.save(txn);
            
            if (isFraud) {
                FraudFlag flag = new FraudFlag();
                flag.setTxnId(txnId);
                flag.setScore(modelScore.probability());
                flag.setLabelPred(true);
                
                Map<String, Object> reasons = new HashMap<>();
                reasons.put("ml_score", modelScore.probability());
                reasons.put("velocity", velocity);
                reasons.put("new_country", isNewCountry);
                reasons.put("new_device", isNewDevice);
                reasons.put("amount", amount);
                flag.setReasonsJson(objectMapper.writeValueAsString(reasons));
                
                fraudFlagRepo.save(flag);
                
                System.out.println("FRAUD: " + txnId + " (score: " + modelScore.probability() + ")");
            }
            
        } catch (Exception e) {
            System.err.println("failed to process transaction: " + e.getMessage());
        }
    }
}
