/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsgemini;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/**
 *
 * @author kim2
 */
// AuditLog class with Observer Pattern
class AuditLog {
    private ArrayList<String> logs = new ArrayList<>();
    private List<AuditLogObserver> observers = new ArrayList<>();

    public void addObserver(AuditLogObserver observer) {
        observers.add(observer);
    }

    public void removeObserver(AuditLogObserver observer) {
        observers.remove(observer);
    }

    public void logAction(String logEntry) {
        logs.add(new Date().toString() + " - " + logEntry);
        for (AuditLogObserver observer : observers) {
            observer.onLogEvent(logEntry);
        }
    }

    public void showLogs() {
        for (String log : logs) {
            System.out.println(log);
        }
    }
}
