/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
class Subject {
    private List<Observer> observers = new ArrayList<>();
    
    public void attach(Observer observer) {
        observers.add(observer);
    }
    
    public void detach(Observer observer) {
        observers.remove(observer);
    }
    
    protected void notifyObservers(String message) {
        for (Observer observer : observers) {
            observer.update(message);
        }
    }
}