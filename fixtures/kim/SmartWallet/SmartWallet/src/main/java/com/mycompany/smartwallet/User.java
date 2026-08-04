/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.smartwallet;

import java.util.HashMap;
import java.util.Map;

/**
 *
 * @author kim2
 */
public class User {
    private String name;
    private String password;
    private Map<String, Wallet> wallets;
    private AuditLog auditLog;

    public User(String name, String password) {
        this.name = name;
        this.password = password;
        this.wallets = new HashMap<>();
        this.auditLog = new AuditLog();
        auditLog.logAction("User created: " + name);
    }

    public boolean authenticate(String password) {
        return this.password.equals(password);
    }

    public void addWallet(String currency) {
        if (!wallets.containsKey(currency)) {
            wallets.put(currency, new Wallet(currency));
            auditLog.logAction("Wallet added: " + currency);
        }
    }

    public Wallet getWallet(String currency) {
        return wallets.get(currency);
    }

    public void showAllBalances() {
        wallets.forEach((currency, wallet) -> {
            wallet.showBalance();
        });
    }    
}
