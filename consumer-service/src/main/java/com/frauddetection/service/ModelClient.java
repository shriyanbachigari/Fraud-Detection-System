package com.frauddetection.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.HashMap;
import java.util.Map;

@Service
public class ModelClient {
    
    private final WebClient webClient;
    
    public ModelClient(@Value("${ml-api.url}") String mlApiUrl) {
        this.webClient = WebClient.builder()
            .baseUrl(mlApiUrl)
            .build();
    }
    
    public ModelScore score(double amount, int hour, int countryNovelty, int deviceNovelty, int velocity) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("amount", amount);
            request.put("hour", hour);
            request.put("country_novelty", countryNovelty);
            request.put("device_novelty", deviceNovelty);
            request.put("user_velocity_60s", velocity);
            
            Map<String, Object> response = webClient.post()
                .uri("/score")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(Map.class)
                .block();
            
            if (response != null) {
                double proba = ((Number) response.get("fraud_probability")).doubleValue();
                boolean isFraud = (Boolean) response.get("is_fraud");
                return new ModelScore(proba, isFraud);
            }
        } catch (Exception e) {
            System.err.println("ml api error: " + e.getMessage());
        }
        
        return new ModelScore(0.0, false);
    }
    
    public record ModelScore(double probability, boolean isFraud) {}
}
