/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsmeta;

import java.util.HashMap;
import java.util.Map;

/**
 *
 * @author kim2
 */
// CurrencyConverter class with Singleton pattern
class CurrencyConverter {
    private static CurrencyConverter instance;
    private static final Map<String, Double> exchangeRates = new HashMap<>();

    private CurrencyConverter() {
        exchangeRates.put("USD_EUR", 0.85);
        exchangeRates.put("EUR_USD", 1.17);
        // Add more exchange rates as needed
    }

    // Singleton pattern: get the single instance
    public static CurrencyConverter getInstance() {
        if (instance == null) {
            instance = new CurrencyConverter();
        }
        return instance;
    }

    public double convert(String fromCurrency, String toCurrency, double amount) {
        String key = fromCurrency + "_" + toCurrency;
        return amount * exchangeRates.getOrDefault(key, 1.0);
    }
}

