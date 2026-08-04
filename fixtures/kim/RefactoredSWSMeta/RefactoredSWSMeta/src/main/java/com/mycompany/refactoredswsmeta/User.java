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
// User class with Factory Method pattern
class User {
    private String name;
    private String password;
    private Map<String, Wallet> wallets;
    private AuditLog auditLog;

    public User(String name, String password) {
        this.name = name;
        this.password = password;
        this.wallets = new HashMap<>();
        this.auditLog = new AuditLog();
        auditLog.addObserver((observable, arg) -> System.out.println("Audit Log: " + arg));
        auditLog.logAction("User created: " + name);
    }

    // Factory Method pattern: create a new wallet instance
    public Wallet addWallet(String currency) {
        if (!wallets.containsKey(currency)) {
            wallets.put(currency, new Wallet(currency));
            auditLog.logAction("Wallet added: " + currency);
        }
        return wallets.get(currency);
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
